# 048 — The sandbox holds on wasmtime 49.0.0

- **Status:** drafted 2026-10-18. Not built. It stands behind spec 032's
  dirent-padding fix (branch `spec/032-dirent-padding`, in review); 048 lands after it.
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
  dirent-padding fix in review (`../reviews/032-dirent-padding-2026-10-18.md`, which masks the
  dirent padding in the raw parity check while the pin is on wasmtime 49.0.0); 025 (a writable
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

1. **The precise wasmtime 49.0.3 rule for `path_rename`, served on every call.** `path_rename` is
   shadowed. When neither path has a trailing slash, the call is forwarded to wasmtime unchanged.
   When either the source or the target path ends in `/`, the shadow requires the **source** to be
   a directory, deciding it **without following the source's final symlink**; if the source is not
   a directory it answers `ENOTDIR` (54) and does not forward, exactly as wasmtime 49.0.3 does on
   non-Linux hosts (`fix-49.0.3-rename-only.diff`: `stat_unchecked(.., FollowSymlinks::No).is_dir()`
   else `is_not_directory()`). A trailing-slash rename of a real directory still succeeds; a
   trailing-slash rename whose source is a symlink or a regular file is refused with `ENOTDIR`, so
   the kernel is never asked to follow a trailing-slash symlink out of the preopen. This changes
   nothing a legitimate program does: trailing slashes on rename paths are rare, and POSIX already
   requires `ENOTDIR` for a non-directory source named with a trailing slash. The rule is enforced
   on every call; it only ever changes an answer where a writable place lets a rename happen at all
   (elsewhere wasmtime already answers `EPERM`/`EROFS`, which the shadow forwards unchanged).

2. **The source's type is read without a side effect, in borrowed guest memory.** To decide "is the
   source a directory, not following its final symlink", the shadow forwards `path_filestat_get`
   with the symlink-follow flag clear (flag bit 0 = 0) on the source directory descriptor and the
   stripped source path, and reads the returned filetype (`DIRECTORY == 3`). wasmtime resolves the
   path inside its own sandbox and, with symlink-follow clear, does not follow the final component,
   so a symlink source reports as a symlink, not as what it points at. The 64-byte filestat needs a
   scratch region in guest memory: the shadow borrows the source path's own buffer (already read
   into the runner), saving its bytes, pointing the forwarded call there, reading the filetype, and
   restoring the saved bytes before returning. The borrow is invisible: the guest is suspended for
   the whole host call, so it never observes the transient write (the trampoline runs synchronously
   on the caller's context, spec 032). If the scratch does not fit (`_Memory.fits` is false) or the
   forwarded stat errors, the shadow refuses with `ENOTDIR` rather than forward — a refusal is
   always safe. The forwards are fuel-neutral by the existing `FUEL_ALLOWANCE` (read the fuel,
   raise it by the allowance, set it back in a `finally`), so a guarded rename spends exactly the
   guest fuel an unguarded one would.

3. **`fd_readdir`'s padding is zeroed on every call.** `fd_readdir` is shadowed on every call. The
   shadow forwards to wasmtime, then, over the bytes wasmtime wrote, zeroes the three padding bytes
   after each entry's `d_type` (the `DIRENT` header is `<QQIB3x>`: `d_next`, `d_ino`, `d_namlen`,
   `d_type`, then three pad bytes at offsets 21–23), walking the buffer by `d_next`/`d_namlen` and
   masking a header the buffer cut short as far as it reaches. This closes the leak on the grant
   and stdlib-zip listings the same way spec 032 already closes it on a mount's own listing: both
   now hand the guest zero padding. The zeroing is host-side work that costs the guest no fuel.

4. **The shadow is carried only while the pin is on wasmtime 49.0.0, and removed when it moves.**
   The guard is a temporary belt, like a carried patch (constitution §4.1 spirit) and like spec
   032's `DIRENT_MASKED` mask. When `uv.lock` moves to a wasmtime-py on wasmtime ≥ 49.0.2 (padding)
   and ≥ 49.0.3 (rename), the corresponding shadow is deleted and the native call is used again. A
   rules check ties the guard to the pin so it cannot be left behind or removed early (criterion 7).
   Facts sheet 12 stays the standing upstream ask (question 86).

5. **Only `path_rename` is fixed; `path_symlink` stays native.** The precise rule of Decision 1 is
   complete: the escape is the *rename* following a trailing-slash symlink, and a symlink a guest
   or the embedder placed is caught at the rename, so refusing symlink *creation* is not needed for
   safety. We take the rule that changes nothing legitimate. Refusing `os.symlink` wherever a
   writable place exists is a defence-in-depth alternative the owner may still choose (question 85):
   it would shadow `path_symlink` to answer `EPERM` on a writable place, a one-method addition to
   the guard linker. Recorded, not taken.

6. **How a call is routed.** A call with mounts keeps spec 032's path unchanged: the mount linker
   (`_mount_linker`, all 29 `SHADOWED` calls) and a `_Files` table with the mounts. A call without
   mounts is routed through a new **guard linker** that shadows exactly `fd_readdir` and
   `path_rename` (the two Decision 3 and 1 touch), leaving the other 27 preview1 calls on
   wasmtime's own fast path; it is given a **guard table**, a `_Files` built with an empty mount
   list, so every descriptor is "not a provider number" and every shadowed call forwards — through
   the same trampoline, bound the same way (`_Files.bind` on the guest's memory with wasmtime's own
   calls from today's linker). The two patched `_Files` methods (Decisions 1 and 3) serve the
   guard table and the mount table alike: a mount call that forwards a `fd_readdir` or `path_rename`
   for a real grant descriptor gets the same fix. The default/read-only call pays only the forward
   on its directory listings (the stdlib-zip scan at start-up, chiefly) and on any rename; its
   `fd_read`, `fd_write`, `path_open` and the rest stay native.

## Intent

On wasmtime 49.0.0, a guest with a writable place still cannot reach a host file outside the folders
it was given, and no listing hands the guest a byte of host memory — the same wall wasmtime 49.0.3
gives, carried in the runner until the pin can move.

## Design

```
src/wasi_python/mounts.py            _Files._path_rename: the 49.0.3 rule (Decisions 1, 2) in the
                                       no-provider-number branch, before the forward; a small
                                       helper reads the source's filetype through a no-follow
                                       path_filestat_get in borrowed guest memory.
                                     _Files._fd_readdir: zero the three padding bytes per entry
                                       after the forward (Decision 3), in the no-provider branch.
src/wasi_python/runner.py            _guard_linker(wt, engine): today's linker plus a shadow over
                                       fd_readdir and path_rename only, defined once per engine,
                                       like _mount_linker; cached in a _guard_linkers dict.
                                     _instance / _drive: when a call has no mounts, build a guard
                                       _Files (empty mounts), set call.table, pick guest_linker =
                                       _guard_linker, and bind the trampoline as for a mount call
                                       (plain = today's linker). A call with mounts is unchanged.
                                     a predicate _has_writable_place(checked) for the Safety text
                                       and, if the owner takes question 85, the symlink shadow.
tests/harness/files.py               masked_dirents / DIRENT_MASKED: drop 21–23 from the mask (the
                                       padding is now zero on grants too, so the parity asserts it
                                       rather than masking it); keep d_ino (8–16) masked.
tests/checks/test_v1_2_*.py          the escape check (criterion 1) and the rule check (criterion 2).
tests/unit/test_runner_mounts.py     the guard-table unit checks (criteria 3, 4, 5).
tests/checks/test_rules.py           the pin-tie check (criterion 7).
README.md                            Safety: the carried guard and what it covers.
SECURITY.md                          the escape is handled by the runner while pinned to 49.0.0.
CHANGELOG.md                         0.1.0a4: Security.
```

A note on the trampoline cost. Every directory listing on a no-mount call now bounces through one
host round-trip (the forward) instead of running natively; a rename does too. The round-trip is
fuel-neutral (Decision 2). The cost is bounded — listings and renames are rare next to reads and
writes, and `path_open`/`fd_read`/`fd_write` stay native — and it is removed when the pin moves
(Decision 4). This is the price of closing the two holes without a wasmtime a user cannot install.

## Scope

In: the `path_rename` rule and the `fd_readdir` padding, on wasmtime 49.0.0, through the guard
linker and guard table on calls without mounts, and through the already-shadowed `_Files` methods on
calls with mounts. Removing the guard when the pin moves (the tie check).

Out: refusing `path_symlink` (question 85, Decision 5, not taken); any other advisory the research
memo found not to reach us (component model, GC, exception handling, `wasi-http`, preview0 — our
guest imports only `wasi_snapshot_preview1` and the one door, EXECUTED); moving the pin itself
(blocked on an upstream wasmtime-py release, facts sheet 12); the set-times host-panic advisory
GHSA-j2g9-4prp-pf6h, which the research memo found unreachable through the guest's CPython
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
   **Seen failing first:** on a kernel that follows a trailing-slash symlink in `renameat` (macOS,
   FreeBSD — detected by a host probe that creates a dir, a symlink to it, renames `link/` and sees
   whether the dir moved), today's code moves the sibling in and the guest reads the canary (the
   research repro). On a kernel that does not follow it (Linux, Windows), today's code already
   refuses, so the check records that it was seen failing on macOS/FreeBSD and asserts the safe
   outcome on every host. (This check counts operations and bytes — the canary's presence and
   contents — never time.)
2. `test_a_trailing_slash_rename_rule` (`tests/checks/test_v1_2_*.py`), host-independent: in a
   writable grant with a real sub-directory `d`, a regular file `f`, and a symlink `s` to `d`:
   `rename("d/", "d2")` succeeds (a real directory, trailing slash); `rename("f/", "x")` and
   `rename("s/", "x")` each raise `NotADirectoryError`; `rename("d", "d3")` (no slash) succeeds.
   **Seen failing first:** on today's code `rename("s/", "x")` either escapes (macOS) or wrongly
   succeeds/behaves per the native kernel; the assertion that it is `ENOTDIR` on every host fails
   until the rule is in place.
3. `test_a_grant_readdir_writes_zero_dirent_padding` (`tests/unit/test_runner_mounts.py`), the
   forwarded (no-provider) sibling of 032's `test_a_mount_writes_zero_dirent_padding`: a guard
   `_Files` (empty mounts) forwards `fd_readdir` on a real directory descriptor over a buffer
   pre-filled with `0xFF`; every entry's bytes 21–23 are zero, on full and cut-short buffers
   (sizes that end inside a header's padding), and nothing past the used length is touched.
   **Seen failing first:** without the zeroing, the `0xFF` padding (or host bytes) survives.
4. `test_the_rename_rule_forward_is_fuel_neutral` (`tests/unit/test_runner_mounts.py`): a metered
   guard call whose shadow forwards a `path_filestat_get` and then a `path_rename` reports the
   guest fuel the unguarded forward would, i.e. the allowance is read and restored around each
   forward (the mechanism 032 proved for its forwards; here for the rename's two forwards).
   **Seen failing first:** if the stat forward leaked the allowance, the guest's `fuel_used` would
   grow by `FUEL_ALLOWANCE` per listing/rename.
5. `test_a_guard_call_leaves_the_other_calls_native` (`tests/unit/test_runner_mounts.py`): the
   guard linker shadows exactly `fd_readdir` and `path_rename`; a guard call's `path_open`,
   `fd_read`, `fd_write`, `fd_seek` reach wasmtime directly (the guard `_Files` records no provider
   call for them). A guard, so the fast path is not widened by mistake.
6. The raw parity check (032's `test_raw_calls_answer_as_a_grant_does`) compares a grant and a
   mount with `DIRENT_MASKED` reduced to `d_ino` (bytes 8–16) only: the padding bytes 21–23 are now
   asserted equal (both zero), not masked. **Seen failing first on 032's masked state** (the
   padding differed, which is why 032 masked it); it passes once the grant's forwarded readdir is
   zeroed too. This is why 048 lands after 032's dirent-padding fix.
7. `test_the_rename_and_readdir_guard_match_the_pin` (`tests/checks/test_rules.py`): while `uv.lock`
   pins a wasmtime < 49.0.2, the `fd_readdir` guard is present; while it pins a wasmtime < 49.0.3,
   the `path_rename` guard is present; at or past those versions the respective guard and its
   checks are gone (Decision 4). The check reads the pinned wasmtime version from `uv.lock` and the
   presence of the guard in the source. A guard so the belt is removed when, and only when, the pin
   moves.
8. `uv run ruff check`, `uv run ruff format --check`, and `uv run pytest` green, with
   `--accept-judge` for the new and changed checks; ratchet vs the base: lost 0, grew 0 (the guard
   is fuel-neutral, so no fuel golden grows; if a byte count moves, it is stated).

## The owner's choices

None open here. This specification decides every choice it needs (constitution §5.2): the precise
49.0.3 rule for `path_rename` (Decision 1), the source-type read in borrowed guest memory
(Decision 2), `fd_readdir` padding zeroed on every call (Decision 3), the guard carried only while
the pin is on 49.0.0 and removed when it moves (Decision 4), and `path_symlink` left native with
the defence-in-depth alternative recorded (Decision 5).

Four owner matters are already recorded as owner questions 84 to 87
(`../questions-for-the-owner.md`), raised by the research memo, and this specification does not
pre-empt them: whether 0.1.0a4 ships with this guard or documents the escape (84); whether to also
refuse `path_symlink` (85, Decision 5 records the alternative and how to take it); keeping facts
sheet 12 as the standing upstream ask and removing the guard when the pin moves (86, Decision 4);
and the outward-facing handling of the already-published 0.1.0a3 (87), which the agent does not act
on. The build proceeds on the recommended answers (land the guard; the precise rule only); if the
owner answers 84 or 85 otherwise, the change is small and named in Decision 5.

## Landing notes

Not built.
