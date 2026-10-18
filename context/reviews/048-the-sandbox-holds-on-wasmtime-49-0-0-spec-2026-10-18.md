# Review of spec 048 before build: the sandbox holds on wasmtime 49.0.0

- **Reviewed:** `context/specifications/048-the-sandbox-holds-on-wasmtime-49-0-0.md` as drafted
  at `c5cd693` (main), pre-build design review (constitution §5.6).
- **Reviewer:** a fresh agent (Claude Opus 5.5) that did not write the specification or the
  research memo.
- **Read:** `AGENTS.md`; constitution §4.1, §4.13–§4.15, §5.2, §5.5–§5.7; the research memo
  `research/2026-10-18-wasmtime-49-advisories.md` and its evidence (`fix-49.0.3-rename-only.diff`,
  `releases.txt`, `advisories/GHSA-m9f7-9w4p-gv38.json`, `advisories/GHSA-96f6-r43r-8c24.json`);
  owner questions 84–87; `src/wasi_python/mounts.py` and `src/wasi_python/runner.py` on main
  (`_Files`, `forward`, `_Memory`, `_path_rename`, `_fd_readdir`, `_instance`, `_drive`,
  `_shared`, `_mount_linker`); `tests/harness/files.py` and `tests/unit/test_runner_mounts.py` on
  `spec/032-dirent-padding` (`d5ee40f`); spec 034's status; wasmtime **v49.0.3** in
  `context/prior_art/wasmtime-v49` (`crates/wasi/src/filesystem/primitives/via_parent/rename.rs`,
  `rustix/fs/dir_utils.rs`, `crates/wasi/src/p1.rs` `fd_readdir`,
  `crates/test-programs/src/bin/p1_path_rename_trailing_slashes.rs`).
- **Executed:** nothing that changes a result. No guest ran in this review. I began a raw
  preview1 prototype in the scratch folder and stopped it before it ran. It is incomplete and was
  not used. So every finding below is READ or INFERRED. None is EXECUTED.

Terms. A **shadow** is a host function defined over a preview1 import. A **forward** is the
shadow
calling wasmtime's own implementation through the trampoline. **49.0.3's rule** is the code in
`via_parent/rename.rs` at tag `v49.0.3`.

## Findings, most severe first

### F1 (high). The design forwards the trailing slash, so it keeps the race that 49.0.3 closes

**Evidence (READ).** In 49.0.3 the non-Linux path first strips trailing slashes from both paths.
Then it checks the source with `stat_unchecked(.., FollowSymlinks::No)`. Then it renames **by the
plain names**. The code comment says why: *"The check isn't atomic with the rename, but whatever
replaces the source in between is still renamed by its plain name."* 49.0.0 (the `-` side of the
diff) puts the `/` back onto the source basename on every Unix before `renameat`. Decision 1 says
the shadow forwards the call "unchanged" once the source passes the check. So 49.0.0 still calls
`renameat(old_dir, "d/", ...)`.

**Why it matters (INFERRED).** Between the shadow's stat and wasmtime's `renameat`, something can
replace the real directory `d` with a symlink `d -> ../outside`. On macOS the kernel then follows
it, and that is the escape again. The guest that made the call is suspended, so it cannot do this
itself. But spec 011 lets calls run on many threads, and an embedder can give two concurrent
calls the same writable grant. Another host process can also change that folder. The window is
small. It is also exactly the window upstream decided to close.

**Fix.** After the check passes, forward with every trailing `/` removed from both paths. The
pointers stay the same and only the lengths get shorter, so nothing is written to guest memory.
Keep at least one byte, as `strip_dir_suffix` does. A forward with no slash makes 49.0.0 rename by
plain names, which is 49.0.3's non-Linux behaviour. Use that one code path on every host: on Linux
it gives the same answers as the kernel check. Say this in Decision 1. Add a unit check that the
forwarded `path_rename` lengths have no trailing `/` when the source passed the check.

### F2 (high). The borrowed scratch is under-specified: it can end the guest, and it overlaps the path

**Evidence (READ).** A preview1 filestat is 64 bytes and must be 8-byte aligned. `FILESTAT` is
`<QQB7xQQQQQ`, and 032's own `_path_filestat_get` calls `_result(memory, out, 64, 8)`. On a
misaligned pointer, `_aligned` raises `_ends("Pointer not aligned to 8")`. That is 032's copy of
what wasmtime does, and it **ends the run**. Decision 2 places the result at "the source path's
own buffer". That pointer is only as aligned as the path. wasi-libc hands `path_rename` a
relative path that sits *inside* the guest's absolute string, after the preopen prefix. For
example, `/work/up/` relative to `/work` starts 6 bytes in. Paths are also usually much shorter
than 64 bytes. So the "buffer" really means 64 bytes starting at the path. Those bytes cover the
path itself and whatever comes after it.

**Why it matters (INFERRED).** If the shadow writes at the path pointer as written, many
trailing-slash renames would trap in wasmtime instead of answering. The guest would die on a
legitimate `os.rename("d/", "e")`. If the shadow rounds the pointer up instead, the result still
overlaps the path that wasmtime reads in the same call. That works only because 49.0.0 happens to
read the path before it writes the result. It also leans on "the guest is suspended" for bytes
the guest never handed over. And it changes answers near the end of memory (`fits` false, which
gives ENOTDIR for a real directory).

**Fix (preferred).** Do not touch guest memory at all. Instantiate, once per call, a second small
trampoline that **defines its own one-page memory** and exports it as `memory`. That trampoline
forwards only `path_filestat_get`. wasmtime's WASI reads and writes through the calling
instance's `memory` export. 032's own design rests on this (memo finding 3). The WASI context
belongs to the store, so descriptor numbers are the same. Copy the already-read source path into
that private memory at offset 64. Ask for the result at offset 0. Read the filetype at byte 16.
The borrow, the save and restore, the alignment rule and the `fits` refusal all disappear. The
same `FUEL_ALLOWANCE` covers it. **If the borrow is kept anyway**, the spec must name an 8-aligned
64-byte region that does not overlap either path, restore it in a `finally`, and add a check with
a deliberately misaligned path pointer.

### F3 (medium). On a stat error the rule answers ENOTDIR, but 49.0.3 returns the stat's own error

**Evidence (READ).** 49.0.3 runs `stat_unchecked(...)?`. A failing stat returns its own error,
such as ENOENT for a missing source or ENOTDIR for a non-directory parent. Only a stat that
*succeeds* on a non-directory gives `is_not_directory()`. Decision 2 refuses every stat error
with ENOTDIR. So the claim "exactly as wasmtime 49.0.3 does" does not hold:
`os.rename("missing/", "x")` would raise `NotADirectoryError` where 49.0.0 and 49.0.3 both raise
`FileNotFoundError`.

**Fix.** Return the stat's errno unchanged. Any non-zero errno means no rename is forwarded, so
this is just as safe. Keep ENOTDIR for a successful stat whose filetype is not `DIRECTORY` (3).
Also state the small remaining difference in errno order. 49.0.3 opens both parents before the
stat, so an error on the new path's parent comes first there. Either match that order (forward
the stat only after a cheap check of the new path) or record the difference as accepted.

### F4 (medium). The pin tie reads the wrong pin and counts versions as if they were ordered

**Evidence (READ).** `pyproject.toml` publishes `wasmtime>=49,<50`. `uv.lock` pins only the
development environment. An embedder that already has wasmtime 49.0.0 installed keeps it after
`pip install wasi-python`, because the constraint is already met. `releases.txt` shows
`v50.0.0-rc.1` on 2026-10-05, *before* 49.0.3 (2026-10-14). The rename advisory lists its patched
versions as `36.0.18, 48.0.6, 49.0.3`, with no 50.x. Criterion 7 reads `uv.lock` and treats any
version "at or past" 49.0.3 as fixed. It also treats wasmtime-py's package version as the version
of the wasmtime it bundles. Facts sheet 12 shows they match for 49.0.0 only.

**Why it matters (INFERRED).** If `uv.lock` moves to a fixed release, the check would let the
guard be deleted while the published wheel still allows 49.0.0, and the hole opens again for
those users. A later move to 50.0.0 would also count as "fixed" when it may not be.

**Fix.** Keep each guard while **the floor in `pyproject.toml`** still allows a vulnerable
wasmtime. Decide "fixed" from an explicit list of patched versions per advisory, written in the
check and citing the advisory JSON. A version not on the list fails the check until someone
reads the advisory again. Say that the spec which moves the pin must record which wasmtime the
wasmtime-py wheel bundles (EXECUTED), because the two version numbers can differ. Alternatively,
gate the guard on the installed wasmtime at run time. That needs a reliable way to read the
version and adds a second code path, so the floor rule is simpler.

### F5 (medium). Criterion 2 is not seen failing first on Linux, and it misses the target-slash cases

**Evidence (READ).** On Linux, 49.0.0 already turns `rename("s/", "x")` and `rename("f/", "x")`
into ENOTDIR, because it puts the slash back and the kernel refuses. What 49.0.0 does *not*
refuse is a slash on the **target only**. It strips the target's slash and renames by plain
names, so `rename("f", "x/")` and `rename("s", "x/")` succeed. 49.0.3 refuses both with ENOTDIR,
and upstream's test program checks exactly those pairs (`"up", "stolen/"`; `"link", "target/"`;
`"file", "target/"`). Criterion 2 lists only source-slash cases. Its "seen failing first" text
for Linux ("wrongly succeeds/behaves per the native kernel") is therefore not true for any case
it lists.

**Fix.** Add `rename("f", "x/")`, `rename("s", "x/")` and `rename("d", "d4/")` (which succeeds).
Then criterion 2 fails first on every host. Also add the in-sandbox-symlink case from upstream:
after the refused renames, `d` and `s` are both still in place. Criterion 1 can then keep its host
probe only to *report* whether the kernel follows the link. Its pass condition is the same
everywhere.

### F6 (medium). A guard table on every call changes `Completed.files` and the stop behaviour

**Evidence (READ).** `_instance` sets `files = table.record()` whenever `table is not None`.
`Completed.files` is documented as "`None` for a call without mounts" (README line 582). A
unit check asserts `done.files is None` for a call without mounts
(`tests/unit/test_runner_mounts.py:478`). Decision 6 gives every call without mounts a guard
`_Files`. Also, the guard's shadows go through `_shared`. That function answers EIO once a call
has stopped, and it raises a pending Ctrl-C at that point. The native `fd_readdir` and
`path_rename` did neither.

**Fix.** Write into the design that a guard table is never reported: `files` stays `None` without
mounts. Easiest is a flag on `_Files`, or keeping the guard table out of the `record()` branch.
State that the Ctrl-C and EIO-after-stop behaviour, which now also applies to these two calls on
plain calls, matches spec 030/015 and is intended. Add criterion 5b: on a call without mounts,
`done.files is None`, and the raw `fd_readdir` and `path_rename` answers (errno, an EFAULT trap,
its message's first line) are the same as today's except for the two fixes. Today's raw parity
table compares a grant with a mount, not before with after. So nothing currently guards the
claim "calls without mounts behave as before".

### F7 (low). The padding walk: step by `d_namlen`, and protect `used`

**Evidence (READ).** Decision 3 says to walk "by `d_next`/`d_namlen`". `d_next` is a cookie, not a
byte offset. The 032 mask walks by `24 + d_namlen`, which is correct. In 49.0.2/49.0.3
(`p1.rs` `fd_readdir`), the entries are written with zero padding, and wiggle then writes
`bufused`. If a guest points `used` inside its own buffer, upstream's `used` value wins. Zeroing
*after* the forward would overwrite it.

**Fix.** Say "walk by `24 + d_namlen`, only within `[buf, buf + used)`". Read `used` after the
forward and write it back after the zeroing, or skip any byte inside `used`'s 4 bytes. Zero only
when the forward returned 0. Criterion 3's cut-short buffers are good. Add one case where `used`
lies inside the buffer.

### F8 (low). Small points of scope and wording

- `_has_writable_place` is planned "for the Safety text and, if the owner takes question 85".
  Nothing built here would call it. §6.4 says build the smallest thing, so leave it out until 85
  is answered.
- Spec 034 (writable mounts, confirmed, not built) also changes `_Files._path_rename`. Name the
  order (048 first, then 034 rebases on it). Note that once this lands, a grant's answer to a
  trailing-slash rename of a non-directory is ENOTDIR. 034's served rename must give that same
  answer for parity.
- The research memo called this "build-class". The spec says it is not. The spec is right by
  AGENTS.md's definition (it touches no `scripts/`, `recipes/`, `SHA256SUMS` or workflow). Say so
  in one line, so the lane does not follow the memo instead.
- The `path_rename` guard runs on *every* call. The memo had it only on calls with a writable
  place. Running it everywhere is simpler and safe: on a read-only place wasmtime refuses with
  EPERM at `renameat` anyway. But a read-only call now does the stat before that EPERM, which
  turns a missing source into ENOENT instead of EPERM. Either check order to match (finding F3),
  or state the change.
- Owner questions: "None open here" is fair for the build. Question 84 is a *release* decision,
  so building and landing can go ahead. Say that 0.1.0a4 waits on 84 and the build does not.

## What holds (READ)

- **The rule itself.** Trailing slash on either path → the source must be a directory, checked
  without following its final link → otherwise ENOTDIR. That is 49.0.3's rule. Using
  `path_filestat_get` with lookup flags 0 on the source directory and the stripped source path
  checks the same object 49.0.3 checks: intermediate links resolve inside the sandbox, and the
  final one is not followed.
- **Coverage.** `_drive` is the only place the guest is instantiated (`runner.py:1845`). The
  preopen identity check uses only `fd_prestat_*` and `fd_filestat_get`. With mounts, the forwarded
  branches of `_path_rename` and `_fd_readdir` serve grants, the private root and the zip folder.
  `_across` already refuses renames that involve a mount. Grants, `root=True`, a host-path root and
  the stdlib zip are all reached through either the guard linker or the mount linker. Upstream
  removed `append_dir_suffix` because rename was its only caller, which supports the claim that
  only `path_rename` needs this fix.
- **Guest memory and concurrency.** Each call has its own store and memory, and wasip1 has no
  threads. No preview1 host call calls back into the guest or grows its memory. The epoch callback
  can stop the run inside a forward, and then nothing reads the guest's memory again. So the
  "suspended" argument holds for *that* guest. It does not cover the host folder shared with other
  calls, which is F1.
- **Fuel.** `forward` reads the fuel, raises it by `FUEL_ALLOWANCE`, and sets it back in a
  `finally`. A host call costs no fuel. So two forwards (stat, then rename) or one forward plus
  zeroing leave `fuel_used` unchanged, and criterion 4 tests the right mechanism. One trampoline
  instantiation per call happens before the fuel cap, as 032 already does for mounts.
- **One builder.** It is about 150 lines in two files plus checks, it is not build-class, and it
  needs no artifact rebuild. One builder can do it, after 032's dirent-padding branch lands.

## Constitution checks

- **§4.1 (patches temporary):** met in spirit. No upstream source is patched, and the guard has a
  removal trigger (fix it as F4 says).
- **§4.4 (two channels):** met. No new import. Only how two preview1 imports are served changes.
- **§4.9 (tests count):** met. Every criterion counts bytes, errnos or fuel.
- **§4.15 (safe by default):** met. It only tightens. No default is loosened.
- **§5.2 (no open questions):** met for the build (see F8, the owner-question point).
- **§5.6 (pre-build review):** this document.
- **§6.1 (keep the wall whole):** **not yet**. Fix F1 and F2 first.

## Disposition (filled in by the author, then confirmed by the reviewer)

The specification was revised against all eight findings (048 Status now cites this review).
Finding by finding:

- **F1 (forward keeps the race): fixed.** Decision 1 now forwards the rename **by plain names** —
  every trailing `/` trimmed from both paths before the forward, the same guest pointers with
  shorter lengths (never below one byte, as `strip_dir_suffix` keeps), writing nothing to guest
  memory. This is wasmtime 49.0.3's non-Linux behaviour (strip, check source `FollowSymlinks::No`,
  rename by plain basenames) and closes the check/rename race, quoting the upstream comment
  ("whatever replaces the source in between is still renamed by its plain name"). One code path on
  every host. Criterion 2 adds the unit-level assertion via the check cases; the builder note to
  assert the forwarded lengths have no trailing `/` is carried in Decision 1's text and the Design
  line for `_Files._path_rename`.

- **F2 (borrowed scratch can end the guest): fixed.** Decision 2 no longer borrows guest memory.
  The source's type is read through a **second, tiny trampoline instantiated per guarded call that
  defines its own one-page `memory`** and imports only `path_filestat_get`; the stripped source
  path is copied to offset 64, the result asked for at offset 0, the filetype read at byte 16. No
  guest byte is read, saved or restored; the alignment and `fits` refusals are gone. The Design
  and the trampoline-cost note are updated (two forwards for a rename: stat, then rename).

- **F3 (stat error → wrong errno): fixed.** Decision 3 passes the forwarded stat's own non-zero
  errno through (so `os.rename("missing/", "x")` raises `FileNotFoundError`, matching 49.0.0 and
  49.0.3), and answers `ENOTDIR` only for a *successful* stat whose filetype is not `DIRECTORY`.
  The small errno-order difference (49.0.3 opens both parents before the stat; the shadow stats the
  source first) is stated and accepted, with no sandbox consequence. The read-only EPERM→ENOENT
  change for a missing source is named here and in F8.

- **F4 (pin tie reads the wrong pin): fixed.** Decision 5 and criterion 7 now read the **floor of
  the `wasmtime` requirement in `pyproject.toml`** (not `uv.lock`), and decide "fixed" from
  **explicit per-advisory lists of patched versions** written in the check and citing the advisory
  JSON (padding `36.0.17, 48.0.4, 49.0.2`; rename `36.0.18, 48.0.6, 49.0.3`), with no "at or past"
  ordering. The spec that moves the pin must record which wasmtime the wasmtime-py wheel bundles.

- **F5 (criterion 2 not failing first on Linux; misses target-slash): fixed.** Criterion 2 adds the
  target-only cases `rename("f","x/")` and `rename("s","x/")` (→ `ENOTDIR`) and `rename("d","d4/")`
  (→ success), plus the in-sandbox check that `d` and `s` stay in place; its "seen failing first"
  now holds on every host (the target-slash cases succeed on today's 49.0.0 everywhere, Linux
  included). Criterion 1's host probe is reduced to *reporting* whether the kernel follows the link;
  its safe outcome is asserted on every host.

- **F6 (guard table changes `Completed.files` and stop behaviour): fixed.** Decision 7 states the
  guard table is **never reported** — `Completed.files` stays `None` without mounts (a flag on
  `_Files` or keeping it out of the `record()` branch) — and that the EIO-after-stop and pending
  Ctrl-C behaviour now reaching these two calls on plain calls is spec 030/015 and intended. New
  criterion **5b** asserts `done.files is None` without mounts and that the raw `fd_readdir`/
  `path_rename` answers match today's native answers but for the two fixes (a before-and-after
  guard the grant-vs-mount parity table does not give).

- **F7 (padding walk and `used`): fixed.** Decision 4 walks by **`24 + d_namlen`** within
  **`[buf, buf + used)`**, zeroes only when the forward returned 0, and leaves the 4 bytes at the
  guest's `used` pointer intact. Criterion 3 adds a case where `used` lies inside the buffer.

- **F8 (small points): fixed.** `_has_writable_place` is dropped (Decision 6, nothing built needs
  it). Spec 034 ordering is named: 048 and 034 both edit `_Files._path_rename`, land one at a time,
  and whichever lands second rebases on the first; after 048 a served trailing-slash rename of a
  non-directory answers `ENOTDIR`, which 034's served rename must match for parity (Status, Scope).
  "Not build-class" is stated in the Kind line and the Design, superseding the research memo's
  label. The read-only EPERM→ENOENT change is recorded (Decision 3). Owner question 84 is marked a
  **release** decision in "The owner's choices": building and landing go ahead; only the 0.1.0a4
  release waits on it.

Headings stay free of the word "question" (`uv run pytest -q tests/checks/test_rules.py` green).
Not committed; awaiting the reviewer's confirmation.

## Verdict

**Not ready as written, but close.** The direction is right and the rule is the right rule. Two
mechanics must change before build: forward by plain names after the check (F1), and read the
source's type without borrowing the guest's memory (F2). F3–F6 are small text and check changes.
F7–F8 are notes for the builder.

One line: the guard copies 49.0.3's check but not its rename by plain names, and its borrowed
scratch can end the guest, so fix those two, return the stat's own errno, tie removal to the
published floor, and add the target-slash cases before building.
