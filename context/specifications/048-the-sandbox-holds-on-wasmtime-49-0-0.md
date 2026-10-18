# 048 — The sandbox holds on wasmtime 49.0.0

- **Status:** drafted 2026-10-18; revised the same day against its pre-build design review
  (`../reviews/048-the-sandbox-holds-on-wasmtime-49-0-0-spec-2026-10-18.md`, eight findings, all
  answered in its Disposition); confirmed for build with conditions, written in (the review's
  Confirmation: C1 in Decision 5 and criterion 7, C2 in Decision 2 and criterion 2; builder notes
  N1 and N2 stay in the review). **Built 2026-10-18** on `spec/048-the-sandbox-holds`
  (Landing notes below); awaiting its build review. Spec 032's dirent-padding fix is now on main
  (`ebc9f53`), so the dependency it stood behind is met. It rebases on spec 034 (writable mounts,
  in build review on branch `spec/034-writable-mounts`) — both edit `_Files._path_rename` — on
  whichever of 048 and 034 lands first (finding F8).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`: a guard linker and the per-call guard table;
  `src/wasi_python/mounts.py`: the `_Files` shadows for `fd_readdir` and `path_rename`), judge
  checks in `tests/checks/` and `tests/unit/`, `tests/harness/files.py`, `README.md` (Safety),
  `SECURITY.md`, `CHANGELOG.md`. **Not build-class** (it touches `src/` and `tests/` only: no
  recipe, no `downloads/SHA256SUMS`, no release workflow, no artifact rebuild). It changes how two
  preview1 calls are served on every call, so it takes the §5.6 pre-build design review, as
  spec 032 did.
- **Depends on:** 032 (the shadow/trampoline machinery: `_mount_linker`, `_trampoline_module`,
  `_Files`, `forward`, `_Memory`, the `SHADOWED`/`SIGNATURES` set, `FUEL_ALLOWANCE`); 032's
  dirent-padding fix, landed on main (`ebc9f53`), which masks the dirent padding in the raw parity
  check while the pin is on wasmtime 49.0.0 (`tests/harness/files.py`, `DIRENT_MASKED`); 025 (a writable
  place is `root=True`, a host-path root, or a writable grant; nothing is writable without one);
  017 (grants, read-only unless they say otherwise); 024 (the root walked and judged); 006 (safe
  by default).
- **Research it stands on:** `../research/2026-10-18-wasmtime-49-advisories.md` (EXECUTED: the
  escape reproduced on arm64 macOS against the frozen artifact set; the readdir padding leak; the
  advisory diff `fix-49.0.3-rename-only.diff`; the per-advisory assessment); the upstream facts
  sheet `../upstream/12-wasmtime-py-on-wasmtime-49-0-3/` (the standing ask for a wasmtime-py
  release on wasmtime ≥ 49.0.3); the owner's direction of 2026-10-17 (a safe runtime for agent
  code, where a writable scratch directory is the common case).

## The problem

wasmtime 49.0.0 is the only wasmtime a `pip install wasi-python` user gets: PyPI's newest
`wasmtime` is 49.0.0 (EXECUTED, PyPI JSON), and our pin is `wasmtime>=49,<50`. Two advisories that
wasmtime fixed after 49.0.0 reach us, and both are confirmed against our own runner.

**GHSA-m9f7-9w4p-gv38 (HIGH): a filesystem sandbox escape.** On a kernel whose `renameat` follows a
symbolic link that has a trailing slash — macOS and FreeBSD, not Linux or Windows — a guest with a
**writable place** (a writable grant, a host-path root, or `root=True`) can escape. It creates a
relative symlink pointing out of its sandbox, e.g. `os.symlink("../outside", "up")`, then renames
the link with a trailing slash, `os.rename("up/", "stolen")`. The kernel follows `up/` out of the
preopen and moves the outside directory *into* the sandbox. EXECUTED on arm64 macOS: a directory
that sat outside every grant was moved in, and the guest read its canary and wrote a new file into
it; `run()` returned exit 0 (the research memo, `repro/transcript.txt`). This breaks a boundary the
README states and the v1.2 judge checks ("the guest cannot follow a symbolic link out", README
line 740): the guest never *opens* through the link; it *renames* it, and the kernel follows it
during `renameat`. It is in `SECURITY.md`'s "In scope". A read-only grant cannot start it (symlink
creation returns EPERM, EXECUTED); the default call has nothing writable, so it cannot either.

**GHSA-96f6-r43r-8c24 (LOW): `fd_readdir` leaks host memory.** wasmtime 49.0.0's `fd_readdir`
copies up to three bytes of uninitialized host memory — the padding after each dirent's `d_type`
— into the guest's buffer, on every directory listing, including the always-present stdlib-zip
folder, even when nothing is granted (found by spec 032's release dry run; the facts sheet and
`evidence/padding.txt`). Spec 032's dirent-padding fix makes a mount write zero padding and masks
those bytes in the raw parity check *while the pin is on 49.0.0*; it does nothing for the native
`fd_readdir` a grant or the zip folder still uses.

wasmtime fixed both — the rename in 49.0.3, the padding in 49.0.2 — but **no wasmtime-py release
carries a wasmtime past 49.0.0**, so we cannot close either by moving the pin today (facts sheet
12). Building our own wasmtime-py on 49.0.3 was considered and rejected in the research memo (§3,
Option B): it would make the published wheel depend on a wasmtime that is not on PyPI, breaking
`pip install wasi-python` (constitution §2.1, §2.4). The mitigation is a host-side shadow, reusing
spec 032's machinery, removed when the pin moves.

## Decisions

1. **The precise wasmtime 49.0.3 rule for `path_rename`, and the forward is by plain names**
   (finding F1). `path_rename` is shadowed. When neither path has a trailing slash, the call is
   forwarded to wasmtime unchanged. When either the source or the target path ends in `/`, the
   shadow requires the **source** to be a directory, deciding it **without following the source's
   final symlink** (Decision 2); if the source is not a directory it answers that reason (Decision
   3) and does not forward. If the source is a directory, the shadow forwards the rename **with
   every trailing `/` trimmed from both paths** — the same guest pointers, only the lengths made
   shorter (never below one byte, as wasmtime's own `strip_dir_suffix` keeps), writing nothing to
   guest memory. wasmtime 49.0.0 then renames by the plain names, which is exactly wasmtime
   49.0.3's non-Linux behaviour (`fix-49.0.3-rename-only.diff`: strip both suffixes, check the
   source `FollowSymlinks::No`, then `rename_unchecked` by the plain basenames). Trimming before
   the forward is what closes the check/rename race: 49.0.3's comment says "whatever replaces the
   source in between is still renamed by its plain name", so even if another concurrent call or
   host process swaps the real directory for a symlink between the shadow's stat and wasmtime's
   `renameat`, the kernel is never handed a trailing-slash name to follow. This is one code path on
   every host: on Linux renaming by plain names gives the kernel the same answers its own
   trailing-slash check would. A trailing-slash rename of a real directory still succeeds; one
   whose source is a symlink or a regular file, or whose target names a non-directory with a
   slash, is refused. This changes nothing a legitimate program does: trailing slashes on rename
   paths are rare, and POSIX already requires `ENOTDIR` for a non-directory named with a trailing
   slash. The rule runs on every call; it only ever changes an answer where a writable place lets
   a rename happen at all (elsewhere wasmtime answers `EPERM`/`EROFS`, except that a read-only
   missing source now reads as its stat's error — see Decision 3 and finding F8).

2. **The source's type is read in a private one-page memory, never in the guest's** (finding F2).
   To decide "is the source a directory, not following its final symlink", the shadow asks
   wasmtime for a `path_filestat_get` with the symlink-follow flag clear (flag bit 0 = 0) on the
   source directory descriptor and the stripped source path. wasmtime resolves the path inside its
   own sandbox and, with symlink-follow clear, does not follow the final component, so a symlink
   source reports as a symlink, not as what it points at. The 64-byte filestat is 8-byte aligned
   and must not touch the guest's memory (borrowing it could trap on a misaligned path pointer and
   end the guest, and it overlaps the very path wasmtime reads). So the stat goes through a
   **second, tiny trampoline instantiated once per guarded call** that defines **its own one-page
   `memory`** (a `(memory 1)` the module exports as `memory`) and imports only `path_filestat_get`.
   wasmtime's WASI reads and writes through the calling instance's `memory` export (spec 032, memo
   finding 3), and the WASI context belongs to the store, so descriptor numbers are the same as
   the guest's. The shadow copies the already-read, stripped source path into this private memory
   at offset 64, asks for the result at offset 0, calls `path_filestat_get` on the stat trampoline,
   and reads the filetype at byte 16 (`FILESTAT` is `<QQB7x…>`, filetype at offset 16). No guest
   byte is read, saved or restored; no alignment or `fits` refusal is needed. The forward is
   fuel-neutral by the existing `FUEL_ALLOWANCE` (read the fuel, raise it by the allowance, set it
   back in a `finally`), as is the rename forward, so a guarded rename spends exactly the guest
   fuel an unguarded one would. The stat trampoline is instantiated before the fuel cap, like the
   main trampoline 032 binds.

   **Once a trailing slash is seen, the rename is never forwarded with it** (condition C2). The
   slash test reads each path's last byte from guest memory; if a path does not fit in guest
   memory, the call is forwarded unchanged (wasmtime cannot read it either, so no rename happens
   and the errno stays as today's). After a slash is seen, any failure to stage the source answers
   an errno and **does not forward**: a source longer than the private page allows (65,536 − 64
   bytes), or longer than `MAX_PATH` if the builder reuses `_Files._path`, answers `ENAMETOOLONG`
   (37). This matters because wasmtime 49.0.0 has no whole-path length limit (it opens the parent
   one component at a time and calls `renameat` on the final name), so a long `./././…/up/`
   forwarded unchanged would skip the rule entirely.

3. **A stat error is passed through; `ENOTDIR` only for a successful stat on a non-directory**
   (finding F3). wasmtime 49.0.3 runs `stat_unchecked(..)?`: a failing stat returns its own error
   (`ENOENT` for a missing source, `ENOTDIR` for a non-directory parent), and only a stat that
   *succeeds* on a non-directory gives `is_not_directory()`. The shadow does the same: if the
   forwarded `path_filestat_get` returns a non-zero errno, that errno is the answer and no rename
   is forwarded (any non-zero errno means no rename, so this is just as safe); if it succeeds and
   the filetype is not `DIRECTORY` (3), the answer is `ENOTDIR` (54); if it succeeds and the
   filetype is a directory, the rename is forwarded by plain names (Decision 1). So
   `os.rename("missing/", "x")` raises `FileNotFoundError`, as both 49.0.0 and 49.0.3 do, not
   `NotADirectoryError`. One small ordering difference is recorded and accepted: 49.0.3 opens both
   parents before it stats, so an error on the *target*'s parent surfaces before the source stat's
   error there; the shadow stats the source first, so when both the target's parent is bad and the
   source is missing, the errno order can differ. No sandbox consequence follows (no rename is
   forwarded in either case). On a **read-only** place this also changes a trailing-slash rename of
   a missing source from `EPERM` to the stat's `ENOENT` (finding F8); the rename still does not
   happen.

4. **`fd_readdir`'s padding is zeroed on every call, and `used` is kept intact** (finding F7).
   `fd_readdir` is shadowed on every call. The shadow forwards to wasmtime and, **only when the
   forward returned errno 0**, reads the written byte count `used` from the guest and, over the
   bytes `[buf, buf + used)` only, zeroes the three padding bytes after each entry's `d_type` (the
   `DIRENT` header is `<QQIB3x>`: `d_next`, `d_ino`, `d_namlen`, `d_type`, then three pad bytes at
   offsets 21–23), **walking by `24 + d_namlen`** (`d_next` is a cookie, not a byte offset) and
   masking a header the buffer cut short as far as it reaches. The 4 bytes wasmtime wrote at the
   guest's `used` pointer are left untouched (the walk reads `used` but never writes inside its
   region, so a guest that points `used` into its own buffer keeps upstream's value). This closes
   the leak on the grant and stdlib-zip listings the same way spec 032 already closes it on a
   mount's own listing: both now hand the guest zero padding. The zeroing is host-side work that
   costs the guest no fuel.

5. **The shadow is carried only while the published floor allows a vulnerable wasmtime, and
   removed when it no longer does** (finding F4). The guard is a temporary belt, like a carried
   patch (constitution §4.1 spirit) and like spec 032's `DIRENT_MASKED` mask. A rules check
   (criterion 7) reads the **floor of the `wasmtime` requirement in `pyproject.toml`** (today
   `>=49,<50`), not `uv.lock` — an embedder who already has 49.0.0 keeps it after
   `pip install wasi-python`, because the floor is already met, so the published floor is what
   decides whether a user can still be on a vulnerable wasmtime. "Fixed" is decided from an
   **explicit list of patched versions per advisory**, written in the check and citing the
   advisory JSON (GHSA-96f6-r43r-8c24: `36.0.17, 48.0.4, 49.0.2`; GHSA-m9f7-9w4p-gv38: `36.0.18,
   48.0.6, 49.0.3`) — not an "at or past" comparison, because wasmtime's releases are not linearly
   ordered (`v50.0.0-rc.1` predates `v49.0.3`, `releases.txt`) and wasmtime-py's own version is
   not the version of the wasmtime it bundles (they match for 49.0.0 only, facts sheet 12). The
   removal predicate (condition C1): a guard may go only when, **for every major.minor line the
   `wasmtime` requirement admits**, that guard's advisory lists a patched version in that line at
   or below the lowest version the requirement admits in that line; if any admitted line has no
   listed version, the guard stays. So `>=49,<50` keeps both guards (49.0.0 is below 49.0.2 and
   49.0.3); `>=49.0.3,<50` lets both go (49.0.2 and 49.0.3 are at or below 49.0.3); `>=49.0.3,<51`
   keeps both, because the 50.x line has no listed patched version. When a guard may go, it and
   its checks are deleted and the native call is used again. The spec that moves the pin must record which wasmtime the
   wasmtime-py wheel bundles (EXECUTED), because the two numbers can differ. Facts sheet 12 stays
   the standing upstream ask (owner question 86).

6. **Only `path_rename` is fixed; `path_symlink` stays native.** The rule of Decision 1 is
   complete: the escape is the *rename* following a trailing-slash symlink, and a symlink a guest
   or the embedder placed is caught at the rename, so refusing symlink *creation* is not needed for
   safety. We take the rule that changes nothing legitimate. Refusing `os.symlink` wherever a
   writable place exists is a defence-in-depth alternative the owner may still choose (owner
   question 85): it would shadow `path_symlink` to answer `EPERM` on a writable place, a
   one-method addition to the guard linker. Recorded, not taken; nothing built here needs a
   writable-place predicate, so none is added (finding F8).

7. **How a call is routed, and a guard table is never reported** (finding F6). A call with mounts
   keeps spec 032's path unchanged: the mount linker (`_mount_linker`, all 29 `SHADOWED` calls) and
   a `_Files` table with the mounts. A call without mounts is routed through a new **guard linker**
   that shadows exactly `fd_readdir` and `path_rename` (the two calls Decisions 4 and 1 touch),
   leaving the other 27 preview1 calls on wasmtime's own fast path; it is given a **guard table**,
   a `_Files` built with an empty mount list, so every descriptor is "not a provider number" and
   both shadowed calls forward — through the same trampoline, bound the same way (`_Files.bind` on
   the guest's memory with wasmtime's own calls from today's linker). The two patched `_Files`
   methods (Decisions 1 and 4) serve the guard table and the mount table alike: a mount call that
   forwards a `fd_readdir` or `path_rename` for a real grant descriptor gets the same fix. A guard
   table is **never reported**: `Completed.files` stays `None` for a call without mounts (README
   line 586, and the existing unit check), because the guard table carries no provider and
   `record()` is not called for it — a flag on `_Files`, or keeping the guard table out of the
   `record()` branch in `_instance`. The guard's two calls go through `_shared`, so, like a mount's
   shadows, they answer EIO once the call has stopped and raise a pending Ctrl-C at the guard
   (specs 030 and 015); the native `fd_readdir`/`path_rename` did neither, and this stop behaviour
   is intended and stated. The default/read-only call pays only the forward on its directory
   listings (the stdlib-zip scan at start-up, chiefly) and on any rename; its `fd_read`,
   `fd_write`, `path_open` and the rest stay native.

## Intent

On wasmtime 49.0.0, a guest with a writable place still cannot reach a host file outside the folders
it was given, and no listing hands the guest a byte of host memory — the same wall wasmtime 49.0.3
gives, carried in the runner until the pin can move.

## Design

This touches `src/` and `tests/` only — no `scripts/`, `recipes/`, `downloads/SHA256SUMS` or
release workflow — so by AGENTS.md's definition it is **not build-class**; the research memo's
"build-class" label is superseded, so the landing lane does not follow it (finding F8).

```
src/wasi_python/mounts.py            _Files._path_rename: the 49.0.3 rule (Decisions 1–3) in the
                                       no-provider-number branch — if either path has a trailing
                                       slash, stat the source no-follow, answer the stat's errno or
                                       ENOTDIR, else forward with the slashes trimmed (same
                                       pointers, shorter lengths).
                                     a helper that reads the source's filetype through a no-follow
                                       path_filestat_get on a per-call stat trampoline with its own
                                       one-page memory (Decision 2) — no guest byte touched.
                                     _Files._fd_readdir: when the forward returns 0, zero the three
                                       padding bytes per entry within [buf, buf+used), walking by
                                       24 + d_namlen, leaving `used` intact (Decision 4).
src/wasi_python/runner.py            _guard_linker(wt, engine): today's linker plus a shadow over
                                       fd_readdir and path_rename only, defined once per engine,
                                       like _mount_linker; cached in a _guard_linkers dict.
                                     _trampoline for the stat: a second tiny module (one-page
                                       memory, imports path_filestat_get) compiled once per engine,
                                       instantiated per guarded call before the fuel cap.
                                     _instance / _drive: when a call has no mounts, build a guard
                                       _Files (empty mounts), set call.table, pick guest_linker =
                                       _guard_linker, and bind the trampoline as for a mount call
                                       (plain = today's linker). The guard table is not reported:
                                       Completed.files stays None without mounts (Decision 7). A
                                       call with mounts is unchanged.
tests/harness/files.py               masked_dirents / DIRENT_MASKED: drop 21–23 from the mask (the
                                       padding is now zero on grants too, so the parity asserts it
                                       rather than masking it); keep d_ino (8–16) masked.
tests/checks/test_v1_2_*.py          the escape check (criterion 1) and the rule check (criterion 2).
tests/unit/test_runner_mounts.py     the guard-table unit checks (criteria 3, 4, 5, 5b).
tests/checks/test_rules.py           the floor-tie check (criterion 7).
README.md                            Safety: the carried guard and what it covers.
SECURITY.md                          the escape is handled by the runner while pinned to 49.0.0.
CHANGELOG.md                         0.1.0a4: Security.
```

A note on the trampoline cost. Every directory listing on a no-mount call now bounces through one
host round-trip (the forward) instead of running natively; a rename does too (two forwards: the
stat, then the rename). The round-trips are fuel-neutral (Decision 2). The cost is bounded —
listings and renames are rare next to reads and writes, and `path_open`/`fd_read`/`fd_write` stay
native — and it is removed when the floor moves (Decision 5). This is the price of closing the two
holes without a wasmtime a user cannot install.

## Scope

In: the `path_rename` rule and the `fd_readdir` padding, on wasmtime 49.0.0, through the guard
linker and guard table on calls without mounts, and through the already-shadowed `_Files` methods on
calls with mounts. Removing each guard when the published floor no longer admits a vulnerable
wasmtime (the floor-tie check). Rebasing on spec 034 (which also edits `_Files._path_rename`):
048 and 034 land one at a time, and whichever lands second rebases on the first; after 048, a
grant's served trailing-slash rename of a non-directory answers `ENOTDIR`, and 034's served rename
must give that same answer for parity (finding F8).

Out: refusing `path_symlink` (owner question 85, Decision 6, not taken); any other advisory the
research memo found not to reach us (component model, GC, exception handling, `wasi-http`, preview0
— our guest imports only `wasi_snapshot_preview1` and the one door, EXECUTED); moving the pin
itself (blocked on an upstream wasmtime-py release, facts sheet 12); the set-times host-panic
advisory GHSA-j2g9-4prp-pf6h, which the research memo found unreachable through the guest's CPython
(EXECUTED). Linux and Windows are unaffected by the escape (the advisory), but the guard runs on
every host so the rule is one code path, and the padding leak is on every host.

## Acceptance criteria

Each check names its file and is seen failing first on today's code (before the guard). File checks
run the guest in a child process as the v1.2 checks do; unit checks drive `_Files` with a fake
caller and no artifacts, as `test_runner_mounts.py` does. Nothing measures wall-clock.

1. `test_a_trailing_slash_symlink_rename_cannot_escape` (`tests/checks/test_v1_2_*.py`): a scratch
   layout of a writable grant and a sibling directory outside every grant holding a canary file.
   The guest runs `os.symlink("../outside", "up"); os.rename("up/", "stolen")`. After the call: the
   rename raised `NotADirectoryError` (errno 54) in the guest; the sibling directory and its canary
   are unchanged on the host; nothing named `stolen` exists in the grant. Parametrized over a
   writable grant and over `root=True` (with the sibling planted under the private root's parent).
   The safe outcome is asserted on **every** host; a host probe (create a dir, a symlink to it,
   rename `link/`, see whether the dir moved) only *reports* in the message whether this kernel
   follows trailing-slash symlinks in `renameat` (macOS/FreeBSD do, Linux/Windows do not).
   **Seen failing first:** on a following kernel, today's code moves the sibling in and the guest
   reads the canary (the research repro, EXECUTED on arm64 macOS); on a non-following kernel the
   symlink source case already refused, so the escape bytes are a no-op there. The rule-level
   failure is covered on every host by criterion 2.
2. `test_a_trailing_slash_rename_rule` (`tests/checks/test_v1_2_*.py`), host-independent: in a
   writable grant with a real sub-directory `d`, a regular file `f`, and a symlink `s` to `d`.
   Source-slash cases: `rename("d/", "d2")` succeeds; `rename("f/", "x")` and `rename("s/", "x")`
   each raise `NotADirectoryError`; `rename("missing/", "x")` raises `FileNotFoundError` (the
   stat's errno, Decision 3). **Target-slash cases, which 49.0.0 does *not* refuse** (it strips the
   target slash and renames by plain names, so these succeed today on every host, including Linux):
   `rename("f", "x/")` and `rename("s", "x/")` each raise `NotADirectoryError`; `rename("d", "d4/")`
   succeeds; `rename("d", "d3")` (no slash) succeeds. After the refused renames, `d` and `s` are
   both still in place (the in-sandbox symlink is not moved either). An over-long case (condition
   C2): a trailing-slash rename whose source path is longer than the stat page allows (or than
   `MAX_PATH`, whichever the build uses), built from repeated `./` components and ending in the
   symlink `s/`, raises `OSError` with errno `ENAMETOOLONG`, and `s` and `d` are still in place.
   **Seen failing first on every
   host:** the target-slash cases `rename("f","x/")` and `rename("s","x/")` succeed on today's
   49.0.0 everywhere, so the assertion that they are `ENOTDIR` fails first on Linux too, not only
   where the source-slash symlink escapes.
3. `test_a_grant_readdir_writes_zero_dirent_padding` (`tests/unit/test_runner_mounts.py`), the
   forwarded (no-provider) sibling of 032's `test_a_mount_writes_zero_dirent_padding`: a guard
   `_Files` (empty mounts) forwards `fd_readdir` on a real directory descriptor over a buffer
   pre-filled with `0xFF`; every entry's bytes 21–23 are zero, walking by `24 + d_namlen` within
   `[buf, buf+used)`, on full and cut-short buffers (sizes that end inside a header's padding).
   Includes a case where the guest's `used` pointer lies **inside** the buffer: its 4 bytes keep
   wasmtime's value (not zeroed), and nothing past `used` is touched. **Seen failing first:**
   without the zeroing, the `0xFF` padding (or host bytes) survives; if the walk overwrote `used`,
   its value would be clobbered.
4. `test_the_rename_rule_forward_is_fuel_neutral` (`tests/unit/test_runner_mounts.py`): a metered
   guard call whose shadow forwards a `path_filestat_get` (on the stat trampoline) and then a
   `path_rename` reports the guest fuel the unguarded forward would, i.e. the allowance is read and
   restored around each forward (the mechanism 032 proved for its forwards; here for the rename's
   two forwards). **Seen failing first:** if a forward leaked the allowance, the guest's
   `fuel_used` would grow by `FUEL_ALLOWANCE` per listing/rename.
5. `test_a_guard_call_leaves_the_other_calls_native` (`tests/unit/test_runner_mounts.py`): the
   guard linker shadows exactly `fd_readdir` and `path_rename`; a guard call's `path_open`,
   `fd_read`, `fd_write`, `fd_seek` reach wasmtime directly (the guard `_Files` records no provider
   call for them). A guard, so the fast path is not widened by mistake.
5b. `test_a_call_without_mounts_is_unchanged_but_for_the_two_fixes`
   (`tests/unit/test_runner_mounts.py`), the before-and-after guard (finding F6): on a call without
   mounts, `done.files is None` (the guard table is never reported, Decision 7); and the raw
   `fd_readdir` and `path_rename` answers — errno, any EFAULT trap and its message's first line —
   match today's native answers, except the two fixes (zeroed padding; the trailing-slash rule).
   The existing raw parity table compares a grant with a mount, not today with after, so nothing
   else guards "a call without mounts behaves as before". **Seen failing first:** on a build where
   the guard table is reported, `done.files` is not `None`.
6. The raw parity check (032's `test_raw_calls_answer_as_a_grant_does`) compares a grant and a
   mount with `DIRENT_MASKED` reduced to `d_ino` (bytes 8–16) only: the padding bytes 21–23 are now
   asserted equal (both zero), not masked. **Seen failing first on main's masked state** (the
   padding differed on a grant, which is why 032 masked it); it passes once the grant's forwarded
   readdir is zeroed too.
7. `test_the_rename_and_readdir_guard_match_the_floor` (`tests/checks/test_rules.py`): the check
   reads the **floor of the `wasmtime` requirement in `pyproject.toml`** (not `uv.lock`), and two
   explicit lists of patched versions written in the check and citing the advisory JSON
   (GHSA-96f6-r43r-8c24: `36.0.17, 48.0.4, 49.0.2`; GHSA-m9f7-9w4p-gv38: `36.0.18, 48.0.6,
   49.0.3`), and applies Decision 5's predicate (condition C1): a guard may go only when every
   major.minor line the requirement admits has a listed patched version at or below the lowest
   version admitted in that line. A table of fixed inputs is checked first: `>=49,<50` → both
   guards required; `>=49.0.3,<50` → both may go; `>=49.0.3,<51` → both required (50.x unlisted).
   Then the real requirement is judged: each guard is present in the source while required, and
   absent with its checks once it may go. A guard so the belt is removed when, and only when, the
   published requirement stops admitting a vulnerable wasmtime.
8. `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest` green, with
   `--accept-judge` for the new and changed checks; ratchet vs the base: lost 0, grew 0 (the guard
   is fuel-neutral, so no fuel golden grows; if a byte count moves, it is stated).

## The owner's choices

None open here. This specification decides every choice it needs (constitution §5.2): the precise
49.0.3 rule for `path_rename`, forwarded by plain names after the check (Decision 1); the
source-type read in a private one-page memory, never the guest's (Decision 2); the stat's own
errno passed through, `ENOTDIR` only for a successful stat on a non-directory (Decision 3);
`fd_readdir` padding zeroed on every call with `used` kept intact (Decision 4); each guard carried
only while the published floor admits a vulnerable wasmtime, removed when it no longer does
(Decision 5); and `path_symlink` left native with the defence-in-depth alternative recorded
(Decision 6).

Four owner matters are already recorded as owner questions 84 to 87
(`../questions-for-the-owner.md`), raised by the research memo, and this specification does not
pre-empt them: whether 0.1.0a4 ships with this guard or documents the escape (84) — a **release**
decision, so building and landing 048 go ahead and only the 0.1.0a4 release waits on it; whether to
also refuse `path_symlink` (85, Decision 6 records the alternative and how to take it); keeping
facts sheet 12 as the standing upstream ask and removing each guard when the floor moves (86,
Decision 5); and the outward-facing handling of the already-published 0.1.0a3 (87), which the agent
does not act on. The build proceeds on the recommended answers (land the guard; the precise rule
only); if the owner answers 85 otherwise, the change is small and named in Decision 6.

## Landing notes

Built 2026-10-18 by a builder agent (Claude Opus 5.5) in the worktree `wasi_python-048`, on
`main` at `a45148c`, on darwin-arm64 (Darwin 25.5.0) with wasmtime-py 49.0.0 (`uv run python -c
"import importlib.metadata as m; print(m.version('wasmtime'))"` → `49.0.0`), against main's frozen
artifact set `build/sets/s-0cdc7b2bd78db6f5` (no artifact was built). Every result below was
EXECUTED there unless labelled otherwise. Not yet reviewed: the build review (`../reviews/`) is
next, then the lane's acceptance (with `--accept-judge`: five judge files changed).

### What changed

- `src/wasi_python/mounts.py`: `GUARDED` (`fd_readdir`, `path_rename`) beside a comment naming
  both advisories; `stat_trampoline_wat()` (imports `path_filestat_get`, defines and exports its
  own `(memory 1 1)`); `_Forwards.stat` and `.page`; `bind` also instantiates the stat
  trampoline; `forward(..., stat=True)` uses the stat trampoline with its own argument slot (N2;
  `release()` drops it with the rest); `_fd_readdir`'s forwarded branch calls `_zero_padding`
  when the forward returned 0; `_path_rename`'s forwarded branch calls `_rename` (the rule) and
  `_source_type` (the stat on the private page); `_plain` (trim trailing `/`, never below one
  byte).
- `src/wasi_python/runner.py`: `_guard_linker` (today's linker plus `_shared("files", EBADF, EIO,
  name)` over the two `GUARDED` calls, cached per engine in `_guard_linkers`);
  `_stat_trampoline_module` (cached in `_stat_trampolines`); `_instance` builds a `_Files` with no
  mounts for every call without mounts and runs it on the guard linker; `files` is
  `table.record()` only when the call has mounts (Decision 7); `_release` clears the two caches.
- Judge: criteria 1 and 2 in `tests/checks/test_v1_2_hostile_guest.py`; 3, 4, 5 and 5b in
  `tests/unit/test_runner_mounts.py`; 7 in `tests/checks/test_rules.py`; `tests/harness/files.py`
  gains `Guarded` (the raw module on the guard linker) and `_OnStack` (`entered`, shared with
  `Mounted`), `DIRENT_MASKED` is `d_ino` only, `masked_dirents` takes the mask; and
  `tests/unit/test_runner_grants.py`'s `_two_sides` serves the parity's grant side through
  `Guarded` (criterion 6: a grant as the runner serves it). One existing check changed with
  Decision 7: spec 032's `test_a_call_without_mounts_is_unchanged` now expects the guard linker
  for a call without mounts and only `fd_readdir`/`path_rename` among its served calls (it
  expected today's linker and no served call).
- `README.md` (Safety: a bullet for the two carried fixes; the mounts bullet no longer says a
  call without mounts "runs exactly as before"; the padding line in *Mounts*; the readdir item
  leaves "Not protected"), `SECURITY.md` ("Upstream advisories the runner handles"),
  `CHANGELOG.md` (0.1.0a4: the known issue becomes a Security entry).

### Builder choices the specification left open

- **The staging limit is `MAX_PATH` (4,096 bytes)**, by reusing `_Files._path` (Decision 2's
  option), and it applies to **both** paths once a slash is seen, not only the source: the
  target must be read whole to trim and decode it, and an unbounded read would let a guest make
  the host copy a path as large as its memory. A slash-named rename with either path past 4,096
  bytes answers `ENAMETOOLONG` and is never forwarded (5b's "to an over-long slash" row).
- **Both paths are decoded before the stat**: invalid UTF-8 answers `EILSEQ`, as wasmtime does
  (it reads both paths before anything else), so 5b's "not UTF-8, slash" row matches today's
  native answer instead of turning into `ENOTDIR`.
- **Criterion 3 writes host-like bytes into the padding itself.** wasmtime 49.0.0's padding is
  whatever its heap holds: in a fresh process, 0 of 1,800 entries carried a non-zero byte
  (a scratch probe, 200 listings × 2 folders), while 5b's run showed `5e e5 78`, `8b 1a 2f` and
  `70 2f 1f`. So a check that waits for the leak would not fail first reliably. Criterion 3 wraps
  `forward` so each forwarded listing then gets `0xA5` in every entry's padding outside `used`;
  without the zeroing that survives every time. 5b and criterion 6 keep the real wasmtime bytes.
- **Criterion 1 runs in a child process whose temporary folder is the check's own
  `tmp_path/temp`** (as `test_the_zip_is_read_only_and_shared` does), so the private root's
  parent, where the `root` case plants `outside`, is inside `tmp_path`. Every grant is inside
  `tmp_path`. Criterion 2 runs in-process with its grant in `tmp_path`.
- **Criterion 7's lines are major versions.** Every wasmtime release is `M.0.P` (READ, the memo's
  `releases.txt`), so the admitted lines are the majors from the floor to the top. A bound with a
  minor version, an open top, or an operator other than `>=`, `<`, `<=`, `==` keeps the guard.
  The check also asserts that each advisory JSON's `patched_versions` equals the list written in
  it, and that a guard is named in `mounts.py` while required (its id, the source's marker); when
  one may go, neither `mounts.py` nor any test may still name its id.

### Builder notes N1 and N2

- **N1 (EXECUTED): wasi-libc passes a target's trailing slash through.** With the guard,
  `os.rename("/work/f", "/work/x/")` and `os.rename("/work/s", "/work/x/")` answer `ENOTDIR` in the
  guest, which only the guard's slash test can produce. So criterion 2's target-slash cases run
  through CPython; no raw driver was needed.
- **N2:** the stat trampoline's handles live in the call's `_Forwards` (`stat`, `page`), with
  their own slot key `"stat"`, and `release()` drops them (it sets `forwards` to `None`).

### Seen failing first

On today's code (before any source change), `build/seen-failing-1.log`:

- Criterion 1 failed in both modes: `{'symlink': 'ok', 'rename': 'ok', 'stolen': True, 'up':
  True, ...}` and the canary was read through `/stolen`. The host probe reported "this kernel
  follows a trailing-slash link in rename". This is the escape, reproduced again for a grant and
  for `root=True`.
- Criterion 2 failed. Each case on a fresh grant, today's code:

  | rename | today (49.0.0) | host after |
  |---|---|---|
  | `f/ -> x` | `ENOTDIR` | unchanged |
  | `s/ -> x` | **ok** | `d` moved to `x` through the link |
  | `missing/ -> x` | `ENOENT` | unchanged |
  | `f -> x/` | **ok** | `f` moved to `x` |
  | `s -> x/` | **ok** | `s` moved to `x` |
  | `./`×2,100 + `s/` `-> x` | **ok** | `d` moved to `x` |
  | `d/ -> d2`, `d -> d4/`, `d -> d3` | ok | renamed |

- Criterion 7 failed: "2 finding(s) … admits a vulnerable wasmtime, and … carries no guard
  naming it".
- Criteria 3, 4, 5, 5b, 6 and the changed 032 check failed with `AttributeError: … no attribute
  '_guard_linker'`.

With the guard plumbing built but its two fixes switched off by a scratch pytest plugin
(`_zero_padding` a no-op, `_Files._rename` a plain forward; not in the repository),
`build/seen-failing-2.log`: criterion 3 failed (`[(0, b'\xa5\xa5\xa5'), (25, …), …]`), 5b failed
(guarded padding `[(0, b'\x8b\x1a/'), (25, b'p/\x1f'), (51, b'\x00\x00\x00')]`), criterion 6
failed (7 readdir rows differ, on padding), and criterion 2 failed as on today's code. With a
second plugin that drops each forward's fuel restore, criterion 4 failed: `('returned 54',
2005) == ('returned 54', -236235)`.

### Each criterion (with the guard)

1. `test_a_trailing_slash_symlink_rename_cannot_escape[grant]` and `[root]` pass: the guest's
   rename raises `NotADirectoryError` (`ENOTDIR`), `outside` holds only `canary.txt` with
   `CANARY`, nothing named `stolen` exists, `up` is still a link, and the child's temporary folder
   holds only what the check planted.
2. `test_a_trailing_slash_rename_rule` passes: `f/`, `s/`, `f -> x/`, `s -> x/` → `ENOTDIR`;
   `missing/` → `ENOENT`; the 4,202-byte `./…/s/` → `ENAMETOOLONG`; then `d`, `s` (still a link
   to `d`) and `f` in place and no `x`; `d/ -> d2`, `d2 -> d`, `d -> d4/`, `d4/ -> d`, `d -> d3`
   all succeed; the grant ends as `d3` (with `in.txt`), `f`, `s`.
3. `test_a_grant_readdir_writes_zero_dirent_padding` passes on the preopen and a folder, buffers
   of 4,096, 22, 23, 25, 47, 48, 50 and 80 bytes; with `used` at `buf + 20` its count is
   wasmtime's and bytes 21 to 24 there are kept; nothing past `used` is touched.
4. `test_the_rename_rule_forward_is_fuel_neutral` passes: 40 rounds of `d/ -> e`, `e/ -> d`,
   `f/ -> e` and a listing end `returned 54` with 2,005 fuel on both linkers, and every cap in
   1 to 39 (step 3) and need − 30 to need + 2 ends the same way with the same fuel.
5. `test_a_guard_call_leaves_the_other_calls_native` passes: of the 35 raw calls, only
   `fd_readdir` and `path_rename` reach the table; no provider call is counted.
5b. `test_a_call_without_mounts_is_unchanged_but_for_the_two_fixes` passes: 32 rows (16
   `fd_readdir`, 16 `path_rename`; errnos, the traps for an unaligned or out-of-memory `used` and
   for paths past memory, and the bytes but `d_ino` and padding) equal today's native answers;
   the guarded padding is zero; the rule's 7 rows answer as Decision 3 says (a read-only
   `missing/` is `ENOENT`, not `EPERM`); `run(["-c", …])` gives `files is None`.
6. `test_raw_calls_answer_as_a_grant_does` passes with `DIRENT_MASKED = range(8, 16)`: the
   padding is compared and equal (both zero).
7. `test_the_rename_and_readdir_guard_match_the_floor` passes: the fixed table (`>=49,<50` both
   stay; `>=49.0.3,<50` both may go; `>=49.0.3,<51` both stay; `>=49.0.2,<50` only the padding
   guard may go; `>=49.0.3` both stay), both JSON lists match, and `wasmtime>=49,<50` keeps both
   guards, which `mounts.py` names.
8. See the scoreboard below.

### The scoreboard

The full judge, `WASI_PYTHON_ARTIFACTS=…/build/sets/s-0cdc7b2bd78db6f5 uv run pytest` on the
finished tree (not accepted; `context/progress/` untouched), `uv run ruff check` and `uv run ruff
format --check` on `src tests recipes/guest`: both clean.

```
wasi_python v1: 220/231 pass · 0 gap · 11 blocked · 0 fail   (unit suite 817/825, 8 skipped)
  v1.1  artifact set        24/25  blocked 1
  v1.2  portable, sealed    48/49  blocked 1
  v1.3  data stack          20/21  blocked 1
  v1.4  embedding           95/95  
  v1.5  rebuild from pins   11/18  blocked 7
  rules constitution rules  22/23  blocked 1
blocked by: oracle 1 · prior-art clones 1 · source tree bzip2 1 · source tree cpython 1 · source tree numpy 1 · source tree pandas 1 · source tree sqlite 1 · source tree xz 1 · source tree zlib 1 · three systems 1 · wheel 1
next: context/research/2026-10-16-reproducible-builds-on-linux.md (unblocks 7, closes 0)
ratchet vs c42410a127: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 4 · grew 0 · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_2_hostile_guest.py, tests/harness/files.py and 2 more
not machine-checked: publication · copying from prior art · numpy/pandas test subsets
  licence content of wasi-libc, llvm-runtimes and unpinned components (presence only) · bundled sub-licences · files a build adds inside a source tree
================= 1037 passed, 19 skipped in 207.50s (0:03:27) =================
```

- **lost 0, grew 0**: no accepted pass is lost and no fuel or byte metric grew, across every
  check that runs a guest, so the guard is fuel-neutral suite-wide (criterion 8). No artifact
  changed.
- **gained 4**: the new checks in `tests/checks/` (criterion 1's two cases, criterion 2,
  criterion 7). The unit checks count in the unit suite (817/825; the 8 skips are Windows-only
  or need what this host lacks, as before).
- **11 blocked**: the fast baseline before the change (`uv run pytest -m "not slow"`) showed 10;
  the 11th is `oracle 1` in v1.3, a slow data-stack check the fast run deselects. Nothing this
  change touches.
- **judge changed**: `tests/checks/test_rules.py`, `tests/checks/test_v1_2_hostile_guest.py`,
  `tests/harness/files.py`, `tests/unit/test_runner_grants.py`, `tests/unit/test_runner_mounts.py`:
  the lane accepts with `--accept-judge`.

### How spec 034 must compose with this

034 (writable mounts, in build review on `spec/034-writable-mounts`) also edits
`_Files._path_rename`. Whichever lands second rebases on the other. After 048:

- `_path_rename`'s branch for two wasmtime numbers calls `self._rename(...)`, not a bare forward.
  034 must keep that call for every rename it forwards to wasmtime, so a grant's rename with a
  trailing slash keeps the rule on calls with mounts too.
- A rename that 034 serves itself (a writable mount) must give the same answers: a trailing `/`
  on either path needs a source that is a folder, judged without following a link (`ENOTDIR`, or
  the source's own errno such as `ENOENT`), and the provider is asked by the plain names. That is
  the parity 034's rows must now meet against `Guarded`, the grant side of
  `test_raw_calls_answer_as_a_grant_does`.
- Any forward 034 adds for `fd_readdir` goes through `_fd_readdir`'s forwarded branch, so it is
  zeroed; a listing 034 serves must write zero padding, which the parity now asserts.
- 034's own `_Files` changes must keep `forward(..., stat=True)`, `_Forwards.stat`/`.page` and
  the stat trampoline in `bind`.

### What the reviewer should look at

- `_rename`'s order: the slash test reads only the last byte and only when both paths fit;
  once a slash is seen nothing is forwarded with it (every failure returns an errno).
- The two choices above that the spec left open (the 4,096 bound on both paths; decoding
  first).
- Criterion 3's injected padding, against the specification's wording ("the `0xFF` padding (or
  host bytes) survives"), and 5b's real-bytes evidence beside it.
- The changed spec 032 check, and `_two_sides`'s grant side moving from plain wasmtime to
  `Guarded`, as judge changes.
- That no cost is visible: the ratchet's "grew 0" is the suite-wide evidence for fuel
  neutrality; a wall-clock cost (one host round trip per listing and rename) was not measured,
  by rule.
