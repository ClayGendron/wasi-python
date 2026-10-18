# 058 — A Windows grant renames a folder over a file

- **Status:** built 2026-10-18; awaiting its build review; Windows evidence by the dry run
  after landing. Drafted and built the same day on `spec/058-windows-renames-a-folder-over-a-file`
  from main `3dfdab4` (Landing notes). It changes neither the guest's imports nor its exports, the
  artifact set nor the build recipe, so §5.6 asks no review before build. A different agent
  reviews the build.
- **Owner:** Clay Gendron
- **Kind:** tests and README; a judge change; not build-class. `tests/checks/test_v1_4_embedding.py`
  (one check's assertions), `tests/harness/files.py` (the per-system table), a new unit case in
  `tests/unit/test_runner_grants.py`, `README.md`, `CHANGELOG.md`. It touches no `src/`,
  `scripts/`, `recipes/`, `downloads/SHA256SUMS` or workflow.
- **Depends on:** 034 (writable mounts; its v1.4 write parity and Decision 12), landed. 032's
  post-landing third part is the precedent (a Windows grant's answer asserted per system, the
  mount's everywhere).
- **Research it stands on:**
  - The release run's log: `build/a4-windows-verify.log` in the main tree (git-ignored), release
    run 39135024458, job "verify (windows-2025)" (EXECUTED there; read whole here). `gh run view
    39135024458` (EXECUTED): "verify (ubuntu-24.04)" and "verify (macos-15)" passed, "verify
    (windows-2025)" failed at "The v1.1 to v1.4 checks on these bytes", and its two later steps
    did not run.
  - wasmtime's own source, `context/prior_art/wasmtime-v49` (tag `v49.0.3`, READ, never edited):
    `crates/wasi/src/filesystem/windows.rs:148-151` (`maybe_dir`), `filesystem.rs:949` (every
    `open_at` calls it), `filesystem.rs:428-447` (Windows errors to WASI's),
    `filesystem/primitives/windows/fs/rename_unchecked.rs` and `remove_file_unchecked.rs`,
    `filesystem/primitives/via_parent/rename.rs`, `crates/test-programs/artifacts/src/lib.rs:13-24`
    and `crates/test-programs/src/bin/p1_path_rename.rs:66-78`. The runner uses wasmtime-py
    49.0.0; `context/research/2026-10-18-wasmtime-49-advisories/fix-49.0.3-files.txt` shows the
    49.0.2 to 49.0.3 diff touches none of these files, and the 49.0.0 to 49.0.2 fixes are listed
    there by title only, so that these files are the same in 49.0.0 is INFERRED, and the
    behaviour they predict is what the release run shows (EXECUTED).
  - Rust's `std::fs::rename` on Windows, `library/std/src/sys/fs/windows.rs:1311-1371` in the
    1.95.0 toolchain's source (READ; the toolchain that built wasmtime-py 49.0.0's library is not
    known, so this corroborates and does not prove).
  - CPython's `Lib/tempfile.py:674-750` (`context/prior_art/cpython`, the 3.14 branch, READ):
    on WASI `os.name` is `posix`, so `TemporaryFile` makes a name and unlinks it while open.
  - Spec 034's Decision 12, acceptance 2 and Landing notes ("Windows was not run"); spec 032's
    "Revised after landing, third part".

## The problem

The 0.1.0a4 release run stopped on Windows. On both binaries, spec 034's
`test_a_writable_mount_answers_as_a_writable_grant_does` failed with two rows (EXECUTED, the log,
lines 293-418 and 556-562):

- **"rename a folder over a file"**: the writable grant answered `None` (success); the writable
  mount answered `["errno", 54]` (`ENOTDIR`), as POSIX does.
- **"sorted listing"**: the grant listed `a.txt, b.txt, copy2.txt, cr.txt, g, h, save.txt,
  tmp7zr2b8wp, tmpwlt5wwnt, x.txt` (the snapshot: `tmp5nmlsrcc, tmp6scne7rq` in those places);
  the mount listed `a.txt, b.txt, copy.txt, copy2.txt, cr.txt, e, final.bin, g, h, save.txt,
  x.txt`.

Every other check passed on Windows (265 passed, 10 skipped); macOS and Linux passed everything.
Windows had never run spec 034's checks before: its landing notes say "Windows was not run", and
the dry run was the lane's.

**Why the rename succeeds.** A grant's `path_rename` without a trailing slash goes to wasmtime
unchanged (spec 048, Decision 1). wasmtime renames on Windows by `std::fs::rename` of the two
full paths, with no check of the kinds (`rename_unchecked.rs`; `via_parent/rename.rs` checks
only when a path ends in `/`). Rust's `rename` on Windows calls `MoveFileExW` with
`MOVEFILE_REPLACE_EXISTING`, then, on `ERROR_ACCESS_DENIED`, `FileRenameInfoEx` with
`FILE_RENAME_FLAG_REPLACE_IF_EXISTS | FILE_RENAME_FLAG_POSIX_SEMANTICS`. Windows lets that
replace a file with a folder. wasmtime's own tests expect it: on Windows they set
`RENAME_DIR_ONTO_FILE`, and `p1_path_rename` then asserts the rename succeeds where Unix asserts
`ENOTDIR` (READ). The release run shows it (EXECUTED).

**Why the listing differs.** Two independent causes.

1. *A consequence of the rename.* After it, `e` is gone and `a.txt` is a folder. So the later
   `shutil.copyfile(a.txt, copy.txt)` fails, and there is no `copy.txt`. That row's grant answer
   is an errno, which the check already leaves out on Windows (a host error), so only the
   listing shows it.
2. *Windows will not remove or rename an open file here.* wasmtime opens every guest path on
   Windows with share mode `FILE_SHARE_READ | FILE_SHARE_WRITE`, never `FILE_SHARE_DELETE`
   (`maybe_dir`, `windows.rs:148-151`, called first by every `open_at`). Removing or renaming a
   file needs `DELETE` access, which another handle without `FILE_SHARE_DELETE` blocks with
   `ERROR_SHARING_VIOLATION` (Windows's sharing rule; INFERRED here, and what the leftover names
   show, EXECUTED); wasmtime maps that error to `ErrorCode::Access`, `EACCES` (READ,
   `filesystem.rs:435`). So:
   - the `TemporaryFile` row: `tempfile` creates `tmpXXXXXXXX`, its unlink fails, it closes the
     file and raises; the file stays (READ, `tempfile.py:743-750`);
   - the `NamedTemporaryFile and os.replace` row: the `os.replace` inside the `with` fails;
     `delete=False` keeps the file; there is no `final.bin`.

   Those are the two `tmp…` names, one per row, in each run. Both rows' grant answers are errnos
   (INFERRED: `EACCES`, 2), already left out on Windows by the host-error rule, so again only the
   listing shows them.

The rename is cause 1's start; cause 2 has nothing to do with it. So "sorted listing" would
differ on Windows even if the rename did not.

## Terms

- **Grant side, mount side.** The check runs one script twice: on a writable `Grant` of a host
  folder (wasmtime answers, so the host's file system decides) and on a writable `Mount` of an
  in-memory provider (the runner answers, the same on every host).
- **Per system.** Asserted with a value chosen by `sys.platform`: `linux`, `darwin` or `win32`.
- **A tempfile name.** `tmp` followed by eight characters from `a` to `z`, `0` to `9` and `_`:
  `tempfile`'s default prefix and its random name sequence.

## Decisions

1. **The mount keeps POSIX's `ENOTDIR` on every host; the grant's answer is the host's, and is
   documented.** A mount's answers are the runner's own. Spec 034 (Decision 12) and 032
   (Decision 6) fix their reference as wasmtime on Linux, and the README's provider contract says
   `rename` "is … `ENOTDIR` (a folder onto a file)". By §6.3 (the same on every WASI host) a
   mount's answer must not depend on the embedder's operating system: a guest that meets a mount
   on a Windows laptop and in a Linux container must see one behaviour, and the provider protocol
   does not know the host at all. Mirroring the host would also make the provider's tree change
   in a way POSIX forbids. So the mount answers 54 everywhere, and the check asserts it
   everywhere.

   **The grant is not shadowed to answer `ENOTDIR` on Windows.** A grant gives the guest the
   host's folder as the host keeps it; that is what a grant is. A shadow would be a
   host-specific branch (§4.3), a check-then-rename race with no security gain (the rename stays
   inside the grant, spec 048's guard already covers what can escape), and a disguise of the
   platform where §4.11 asks for documentation. It is documented instead (Decision 5).

2. **The two rows' grant side is asserted exactly per system; the mount side everywhere; POSIX's
   parity stays as it was.** A table, `WRITE_BY_SYSTEM`, holds each row's grant answer for
   `linux`, `darwin` and `win32`; `WRITE_MOUNT` holds the mount's. For each row the check
   asserts `write_by_system(row, sys.platform)` against the grant and `WRITE_MOUNT[row]` against
   the mount, on every system. A system the table does not name raises `KeyError`, so an unknown
   host fails rather than passes. On POSIX hosts both rows also stay in the parity loop, which
   compares grant with mount, by value and by tree after the row, exactly as before; only on
   Windows does the loop skip them. So no Linux or macOS assertion is removed or loosened: each
   gains an exact value beside its parity. This is 032's precedent ("a Windows grant resolves
   `..` by text, so the deliberate test's grant side is per system; the mount's answer stays
   asserted everywhere") applied to the v1.4 check.

   The table lives in `tests/harness/files.py`, beside `write_tree` and `MemoryProvider`, so the
   check and its unit case read one table.

3. **"sorted listing" is asserted exactly on Windows, with a tempfile name matched in two fixed
   places.** The Windows value is the listing the release run printed, on both binaries, with
   each `tmp…` name replaced by a `TEMPORARY` slot. `answer_matches` treats a slot as one name
   matching `tmp[a-z0-9_]{8}` whole, and everything else as `==`: same length, same names, same
   places. A sorted `tmp…` name always falls between `save.txt` and `x.txt`, so the places are
   fixed. A slot is only ever in the Windows value; on Linux and macOS the listing is compared
   with `==`, unmasked, so a leftover temporary file there still fails.

4. **The `tmp…` names need nothing from the runner, and nothing more from the check.** They are
   the guest's own files in the embedder's folder: a `TemporaryFile` and a `NamedTemporaryFile`
   that Windows would not let go (Decision 5's second item). The runner never touches a grant's
   contents, on any host, and must not start here. They lie under the check's own scratch folder
   (`tempfile.mkdtemp(dir=guest_workdir)`), which the harness owns. The `TemporaryFile` and
   `NamedTemporaryFile` rows themselves stay under the existing rule (a grant answer that is an
   errno is not compared on Windows): their Windows errno is READ and INFERRED, not seen, and the
   exact Windows listing already pins their effect. If a later wasmtime opens files with
   `FILE_SHARE_DELETE`, the listing loses its `tmp…` names, gains `final.bin`, and the check
   fails and names the row: the table then changes, with a reason.

5. **README: what a Windows grant does, beside what a mount does.** Under *Writable mounts*,
   after *What differs from a writable grant*, a short *On Windows* list:
   - `os.rename` of a folder onto a file replaces the file on a Windows grant; a mount never
     does, and answers `ENOTDIR`, as a Linux or macOS grant does;
   - a Windows grant cannot remove or rename a file the guest holds open (`PermissionError`), so
     `tempfile.TemporaryFile` and an `os.replace` inside a `NamedTemporaryFile`'s `with` fail
     there and leave their `tmp…` file; a mount allows both.

   The second item is the same run's other finding: §4.11 asks that a platform's semantics be
   stated, and the README's "`tempfile.TemporaryFile` … behave[s] as on a grant" was true of
   Linux and macOS only, so it now says so. The CHANGELOG gains one entry under
   `0.1.0a5 — unreleased`.

6. **What stays as it is.** The raw write parity in `tests/unit/test_runner_grants.py` already
   compares a non-`WASMTIME_ROWS` row on POSIX only, and passed on Windows in the same run; it is
   not changed. The other rows the rename leaves different on a Windows grant (`copyfile` of
   the folder `a.txt`, the Decision 12 rows `link within` and `utime` on it) are errnos or are
   asserted on POSIX only already. Linux's and macOS's answers are unchanged, and so is
   `LINUX_ROWS_V14`.

## Intent

Make the a4 release's Windows job pass for the right reason: each system's grant answer is
stated exactly, the mount's single answer is held everywhere, and the difference is in the
README, not hidden by a skip.

## Design

- `tests/harness/files.py`: `TEMPORARY`, `TEMPORARY_NAME`, `WRITE_MOUNT`, `WRITE_BY_SYSTEM`,
  `write_by_system(row, system)` and `answer_matches(want, got)`, with a comment naming the
  evidence.
- `tests/checks/test_v1_4_embedding.py`, `test_a_writable_mount_answers_as_a_writable_grant_does`:
  after the `LINUX_ROWS_V14` asserts, one loop over `WRITE_BY_SYSTEM` asserting the grant's
  value per system and the mount's everywhere; in the parity loop, the two rows are skipped
  only when `os.name != "posix"`; the docstring says so.
- `tests/unit/test_runner_grants.py`: `test_the_write_parity_asserts_each_systems_grant`,
  parametrized over `linux`, `darwin` and `win32`, with the release run's Windows listing as
  `WINDOWS_LISTING`. It runs on all three systems in the `verify` job and needs no artifacts.
- `README.md`, `CHANGELOG.md` as Decision 5 says.

## Scope

In: the one v1.4 check, its table and unit case, the README and CHANGELOG. Out: the runner, the
raw parity, any shadow of a grant, any other Windows answer the release run did not show.

## Acceptance criteria

1. `test_the_write_parity_asserts_each_systems_grant[linux]`, `[darwin]` and `[win32]` (unit)
   pass: Linux and macOS get `["errno", 54]` and the mount's listing; Windows gets `None` and the
   release run's listing, matched for both runs' `tmp…` names; a slot refuses a name one
   character short or long, upper case, or `final.bin`, and a listing one name short; the mount's
   answers are 54 and its listing; `freebsd` raises `KeyError`. Seen failing before the table
   existed (3 failed) and with a stand-in table whose `win32` answer is parity's 54 (1 failed,
   `[win32]`).
2. `test_a_writable_mount_answers_as_a_writable_grant_does[plain]` and `[snapshot]` (v1.4) pass
   on macOS. Seen failing with a stand-in that selects the `win32` answers on macOS (2 failed,
   `AssertionError: ('rename a folder over a file', …, ['errno', 54])`).
3. On Linux and macOS both rows are still compared as parity, value and tree, and now also
   against the table's exact value (the diff; the reviewer reads it).
4. README: the *On Windows* list and the qualified `tempfile` sentence. CHANGELOG: one entry
   under `0.1.0a5 — unreleased`.
5. The full judge in the worktree, without `--accept`: no pass lost, nothing grows, the judge
   change named; `ruff check` and `ruff format --check` green.
6. After landing (the lane's): a release dry run whose "verify (windows-2025)" job passes this
   check on both binaries.

## Landing notes

**Built 2026-10-18** on `spec/058-windows-renames-a-folder-over-a-file` from main `3dfdab4`, in
the worktree `wasi_python-058`, against the frozen set
`build/sets/s-c4190ca065ada03a` (the main tree's). The build is `122cd6f`; these notes are the
commit after it.

- **Check first.** The unit case was written before the table: `3 failed` (no
  `write_by_system`), EXECUTED. With the table: `3 passed`. With a stand-in table whose `win32`
  rename answer is parity's `["errno", 54]`: `1 failed, 2 passed`, `[win32]`, `assert ['errno',
  54] is None` (EXECUTED, `build/058-standin-unit.log`; the table restored after).
- **The v1.4 check on macOS**, both binaries: `2 passed` (EXECUTED, `build/058-check.log`): the
  macOS grant answers 54 and lists exactly the mount's eleven names, as the table says. With a
  stand-in that selects the `win32` answers on macOS: `2 failed`, `AssertionError: ('rename a
  folder over a file', 'darwin', ['errno', 54])` (EXECUTED, `build/058-standin-check.log`; the
  stand-in prints the real `sys.platform` and asks for Windows's `None`; restored after).
- **Linux and Windows were not run here.** Linux's grant answers are the parity's, which passed
  in release run 39135024458's "verify (ubuntu-24.04)" (EXECUTED there): both rows compared
  equal with the mount, whose values the table holds. Windows's are the values that run printed
  (EXECUTED there); that the check now passes on Windows is INFERRED from the same log: the
  check reached its last assertion there, and its `differ` held exactly these two rows, which
  Windows now skips in the parity loop and asserts against the values it printed. The first
  Windows run of the change is the dry run after landing (acceptance 6).
- **The judge** (`build/judge-058.log`, the full `uv run pytest`, no `--accept`): `wasi_python
  v1: 300/343 pass · 0 gap · 42 blocked · 1 fail (unit suite 1059/1067, 8 skipped)`, `ratchet vs
  323ad21aa5: lost 1 · absent 0 · unrun 0 · unrun locally 28 · gained 0 · grew 0 · upstream unrun
  31 · judge changed: tests/checks/test_v1_4_embedding.py, tests/harness/files.py,
  tests/unit/test_runner_grants.py`, `1 failed, 1359 passed, 50 skipped`. The blocked checks
  are the worktree's missing source trees and clones (`source tree numpy 17 · source tree pandas
  16 · …`), as in any worktree. **The one failure is not this change's:**
  `test_a_deadline_during_a_door_call_under_cancel_is_named` (spec 030) ended `deadline` before
  its door call, at load average about 89 (EXECUTED, `uptime`); it waits on a wall-clock
  deadline, and this diff touches neither it nor `src/`. Alone, right after, it passed 3 of 3
  (EXECUTED). The lane's judge on the exact commit decides. `ruff check` and `ruff format
  --check` on `src/` and `tests/` are clean.
- **Not done here:** no `--accept`, no push, no rebase. The review gets this specification and
  `git diff 3dfdab4..` on this branch.
