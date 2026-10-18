# Review of 034 — Writable mounts (the build; also a security review)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  its pre-build review or its confirmation. I read `AGENTS.md`, the constitution, the threat
  model (`../research/2026-10-16-a-principal-engineers-direction.md` §2), specification 034 with
  its landing notes, its pre-build review with the Disposition, the Confirmation and the lane's
  note (`034-writable-mounts-spec-2026-10-17.md`), 032's build and security review
  (`032-a-filesystem-provider-2026-10-17.md`, for F1's class and the frame), the wasmtime 49
  advisories memo (`../research/2026-10-18-wasmtime-49-advisories.md`), spec 048 as revised on
  main (`c42410a`) and its pre-build review, and questions 71 and 72. I read the diff
  (`git log -p 987012e..HEAD`): all of `_Files` in `src/wasi_python/mounts.py` as built, and in
  `runner.py` `_check_mounts`, `_instance`, `_home_folder`, `_stop_async_calls` and
  `_ctrl_c_watched`; `tests/harness/files.py`; the new checks. I read wasmtime 49's
  `p1.rs:2038-2050` (`path_create_directory`), `filesystem.rs:852-861`
  (`create_directory_at`) and cap-primitives as vendored there
  (`filesystem/primitives/via_parent/create_dir.rs`, `via_parent/open_parent.rs`,
  `rustix/fs/mod.rs:49`, `windows/fs/mod.rs:29`). Each claim is labelled EXECUTED, READ or
  INFERRED.
- **Reviewed:** commits `bb354ba`, `2fcfbee`, `7588daa`, `7bad2d3` on `spec/034-writable-mounts`
  in the worktree `../wasi_python-034`, on `987012e`. The files as reviewed:
  `mounts.py` SHA-256 `a6a0ed929a86…`, `runner.py` `620389e3ab9d…` (EXECUTED, `shasum`; the same
  hashes the landing notes name).
- **Ran (EXECUTED, darwin-arm64, `uv run`, wasmtime-py 49.0.0, the frozen set
  `build/sets/s-8d84b3b190fe9bce` read only; `scripts/build.sh` not run).** Scripts and outputs
  are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/rv034/`:
  - `judge.log`: `uv sync`, then `WASI_PYTHON_ARTIFACTS=… uv run pytest`, no flags; `uv run ruff
    check src tests`; `uv run ruff format --check src tests`.
  - `hostile_write.py` → `hostile_write.txt`: nine hostile provider answers (two fake `Errno`s,
    `0`, `False`, `b""`, a coroutine, an object whose metaclass `__name__` raises, an exception
    with a raising metaclass name, an exception whose `str()` is a hostile `str` subclass) to the
    write half at five places (the create at open, the close, `mkdir`, `rename`, the walk), through
    `run()`.
  - `hostile_write_m1.py` → `hostile_write_m1.txt`: the same, on a copy of the built source with
    mutant M1 (below), to show what the judge would let through.
  - `escape.py` → `escape.txt`: renames and links between a writable mount and a writable grant,
    a read-only grant, the zip and a private root (`root=True`), with trailing slashes and a
    symlink planted through the writable grant; the host trees compared before and after.
  - `escape_forward.py` → `escape_forward.txt`: GHSA-m9f7-9w4p-gv38's rename, grant to grant, in
    a call with and without a writable mount (scratch folders only).
  - `slash_rows.py` → `slash_rows.txt`: the trailing-slash rename rows, grant against mount.
  - `bounds.py` → `bounds.txt`: 1,100 writing opens then a cancel (the walk's bound); the host
    memory of one growth to a 64 MiB bound (`tracemalloc`).
  - `unlinked_ending.py` → `unlinked_ending.txt`: two scenarios run on the built source and on
    copies with mutants M5 and M6 (below), to show what each would let through.
  - `guards.py` → `guards.txt`: the implementer's guard script (`../034-build/guards.py`, read
    first), re-run by me: each of the fifteen guards removed alone, its named checks run, the
    files restored byte for byte.
  - `mutants.py` → `mutants.txt`, `mutants2.txt`: seventeen one-line mutants of my own, each applied alone to the worktree's
    `mounts.py` or `runner.py` (its text asserted to occur once), the four mount test files run,
    the file written back and checked by SHA-256. Probes that ran while mutants were in the
    worktree used a `git archive HEAD` copy (`src034/`, checked by `__file__`). The first run's
    failure parser missed test ids containing spaces, so the six mutants it reported as
    surviving were run again with a summary-line count (`mutants2.txt`); one of them (M18) is in
    fact caught.
  After every run `git status` in the worktree was clean and both hashes matched.
  The implementer's container scripts and probes (`../034-build/`) were read, and the wasmtime
  wheel there hashed (EXECUTED: `263b924576d9…`, as `uv.lock:126`).

## The judge

EXECUTED (`judge.log`, exit 0):

```
wasi_python v1: 230/241 pass · 0 gap · 11 blocked · 0 fail   (unit suite 649/657, 8 skipped)
  v1.4  embedding           103/103
ratchet vs 789c841673: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 18 · grew 0 · judge changed: tests/checks/test_v1_2_hostile_guest.py, tests/checks/test_v1_4_embedding.py, tests/harness/files.py and 2 more
================= 879 passed, 19 skipped in 206.08s (0:03:26) ==================
```

The landing notes' numbers reproduce exactly. `ruff check`: all checks passed; `ruff format
--check`: 59 files already formatted. No progress file was written.

**The branch no longer merges cleanly with main** (EXECUTED, `git merge-tree --write-tree main
HEAD`: exit 1, conflicts in `CHANGELOG.md`, `tests/checks/test_v1_4_embedding.py` and
`tests/unit/test_runner_mounts.py`). Main has since gained 032's dirent-padding fix (`ebc9f53`)
and spec 031 (`64663de`). `mounts.py` and `runner.py` are untouched on main since `987012e`
(EXECUTED, `git diff --stat`), and main's new tests add no three-key `calls` literal (EXECUTED,
grep), so Decision 11's judge change needs no new rewrite. The lane rebases, resolves the three
files, and compares the result with this diff.

## Findings, most severe first

### F1 — Medium. Two of Decision 7 and 8's rules are built right but guarded by no check: the walk skips unlinked files, and descriptors follow only a rename that succeeded

Both rules protect the embedder's store, threat-model asset 4 (the integrity of the result).
The built code keeps both (READ: `walk`, `mounts.py:469`, skips `entry.unlinked`;
`_path_rename`, `mounts.py:1628-1630`, and `_namespace`, `:1472-1474`, call `_follow` only on
`errno == 0`). But removing either fails nothing. EXECUTED (`mutants2.txt`, the four mount test
files, 224 checks):

```
M5 rename follows even when refused: ['224 passed, 2 skipped …'] 0 failed
M6 the walk writes back unlinked files: ['224 passed, 2 skipped …'] 0 failed
```

What each would do, EXECUTED (`unlinked_ending.txt`). Scenario A: a guest writes `stale` to
`/w/a.txt`, then `os.replace("/w/b.txt", "/w/a.txt")` while the descriptor is open, opens a
`TemporaryFile`, and leaves by `os._exit(0)` with neither closed. Scenario B: the provider
refuses `rename("/a.txt", "/b.txt")` with `EACCES` while the guest holds `/a.txt` open with
`data` written; then it closes.

```
src034 (built)  A: {'/a.txt': b'new'}                               B: {'/a.txt': b'data'}
M6              A: {'/a.txt': b'stale', '/tmphsik4_79': b'temp'}     (B as built)
M5              (A as built)                                         B: {'/a.txt': b'', '/b.txt': b'data'}
```

Under M6 the walk overwrites the file the guest renamed into place with the stale bytes of the
file it replaced, and re-creates a removed temporary file. Under M5 the bytes go to a name the
provider refused, and the real file is left empty. The checks that exist cover the close (M12
is caught by six checks) but not the ending: acceptance 9 closes every file it opens, and
acceptance 5's guest never renames or removes.

**Fix.** Two checks, each seen failing on its mutant first. (a) In acceptance 9 or 5: a file
replaced by a rename while open, and a file removed while open, both left open at an ending
that is not a close (`os._exit`, or a cancel through the door): the provider holds the
replacement's bytes, no temp name is left, and the walk makes no `write`. (b) In acceptance 9 or
the raw unit table: a rename the provider refuses, with a descriptor open at `src` (and one at
`dst`): the close writes back to `src` only, and the `dst` descriptor still writes back. The
same for a refused `remove` (no unlinking).

### F2 — Medium-low. The write half's answers are judged by real type, but no check holds it (032's F1 class)

032's build review (F1) made "every answer judged by its real type" the rule, and acceptance 7's
table checks it for the read half. `_made` follows it for the write half (READ,
`mounts.py:614-634`: `answer is None`, `type(answer) is Errno`, else `_bad` inside the
boundary). It holds against every hostile answer I tried, at the create, the close, `mkdir`,
`rename` and the walk: 45 of 45 give the guest `EIO`, one `FileFault` and one `RefusedWrite`
with `cause == "fault"`, and `run` raises nothing (EXECUTED, `hostile_write.txt`: two fake
`Errno`s, `0`, `False`, `b""`, a coroutine with no "never awaited" warning under
`warnings.simplefilter("error")`, an answer whose metaclass `__name__` raises, an exception with
a raising metaclass name, an exception whose `str()` is a hostile `str` subclass).

No check guards it. EXECUTED (`mutants2.txt`): M1 (`isinstance(answer, Errno)` in `_made`) and
M2 (any falsy answer is success) each leave all 224 checks passing. Under M1 (EXECUTED,
`hostile_write_m1.txt`) a fake `Errno` whose `__int__` is 0 gives the guest **success** for a
write the provider did not make, at open, close, `mkdir`, `rename` and the walk, with no fault;
one of `2**32 + 8` gives the guest `EBADF` (8), outside the closed set; and in both cases
`done.files.refused[i].errno` is the provider's own object, not an `Errno`, so the embedder's
later reading of the record runs provider code. The provider is the embedder's code, not the
adversary, so this is the robustness class 032 judged Medium; it is lower here only because the
code is right today.

**Fix.** Add write-half rows to acceptance 7's table (`test_a_provider_fault_never_escapes`) or a
sibling: the two fake `Errno`s, `0`, a coroutine and an exception with a raising metaclass name,
each for `write` at open, at close and in the walk, and for one namespace call; each `EIO` to the
guest, one fault, one `RefusedWrite(..., Errno.EIO, at, "fault")`, `run` raises nothing. See M1
and M2 fail it.

### F3 — Low-medium. How 034 and 048 must compose

READ and EXECUTED:

- **034 adds no way to the host through a rename.** Within a mount, a rename is one provider
  call on two normalized paths (`_path_rename`); no host `renameat` happens. Between a mount and
  any other descriptor, `_across` answers `EXDEV` or `EPERM` and forwards only
  `fd_fdstat_set_rights(fd, 0, 0)`, `fd_allocate(fd, 0, 0)` and `path_create_directory(fd, "")`
  as probes, never `path_rename` or `path_link` (READ, `mounts.py:1552-1590`). A mount has no
  links (`path_symlink` is `ENOTSUP`). EXECUTED (`escape.txt`): with a symlink `up -> ../outside`
  planted through a writable grant, `rename("/g/up/", "/w/stolen")`, `rename("/g/up",
  "/w/stolen")`, `rename("/w/dir/", "/g/stolen")`, `rename("/w/a.txt", "/g/up/")` and
  `rename("/w/a.txt", "/g/sub/x")` are all 75; to a read-only grant and to the zip, 63; links
  both ways, 75; a climb from the mount's preopen to `../g/up/`, 63. The host tree after differs
  from before only by the grant's own symlink, which the guest made through the grant.
- **The advisory's rename still works in a mounted call, as without one.** `_path_rename`
  forwards a rename between two wasmtime numbers unchanged (`mounts.py:1596-1598`). EXECUTED
  (`escape_forward.txt`, scratch folders only): `os.symlink("../outside", "/g/up")` then
  `os.rename("/g/up/", "/g/stolen")` moves `outside` into the grant **with and without** a
  writable mount. So 034 neither opens nor closes GHSA-m9f7-9w4p-gv38. 048's rule belongs in that
  forward branch, which is the only place 034 forwards a rename; nothing in 034's served branch or
  `_across` needs it for safety.
- **Parity rows that change when 048 lands.** Today a grant and a mount both answer 0 for a file
  renamed to a name with a trailing `/` (EXECUTED, `slash_rows.txt`: `'a.txt' → 'newname/'`,
  `'a.txt' → 'b.txt/'`, `'a.txt' → 'a.txt/'`, all `grant 0, mount 0`). Under 49.0.3's rule, which
  048 carries, a trailing `/` on either path requires the source to be a folder, so the grant
  will answer `ENOTDIR` (54) on those three rows (INFERRED from 048's Decision 1 and
  `fix-49.0.3-rename-only.diff`). The mount follows the builder's choice "its destination's
  trailing `/` is ignored", so `test_raw_write_calls_answer_as_a_writable_grant_does` will fail
  on whichever of the two lands second. 048 already names this (its Scope).
- **The probe `_wasmtime_writable` is untouched by 048** (048 shadows `path_rename` and
  `fd_readdir` only).

**Fix (for whichever lands second, with the lane).** The forward branch of `_path_rename` takes
048's rule, forwarding by plain names. 034's served rename takes 49.0.3's: a trailing `/` on
either path, then one `stat` of the source, `ENOTDIR` unless it is a folder. The three rows
above then agree on 54. Name the order in the landing notes.

### F4 — Low. Growing a buffer briefly takes twice its size, and a grown buffer holds more than `staged` counts

Decision 4 judges growth on the new size before any byte is allocated, and that holds (the judge;
my M14 fails `test_writes_are_bounded`). But the growth itself is `data.extend(bytes(n))`
(`mounts.py:1007`, `:1113`): a temporary of the gap's size, then the buffer's growth.
EXECUTED (`bounds.txt`, `tracemalloc`, a 64 MiB bound):

```
set_size to 67108864: errno 0; held after 1.00 x; peak 2.00 x the size; table staged 67108864
pwrite gap to 67108864: errno 0; held after 1.13 x; peak 2.00 x the size; table staged 67108864
```

So one call can briefly hold the bound plus one more buffer of the gap's size, and a buffer grown
by a gap write holds about 1.13 times what `staged` counts (`bytearray`'s over-allocation). 032's
F2 asked that a listing count what it holds; a buffer does not. Decision 10 already allows one
transient buffer copy at a write-back, and this is the same order, so it is Low. **Fix:** grow
without the temporary (for example by slice assignment from a reused zero block, or resizing in
place), and either count `sys.getsizeof(data)` in `held` or say in Decision 10 and the README that
the bound counts a buffer's length, with up to an eighth more held and one more buffer during a
growth.

### F5 — Info. Question 71 is still open; what the build does meanwhile

The build does exactly what Decision 8 proposes (READ `walk` and `_instance`; EXECUTED in the
judge's acceptance 5): after a deadline or a cancel the walk writes back every dirty buffer that is
not unlinked, owed buffers included; it makes no call when the call raises, when a Ctrl-C is
pending, or once the exit hook has run. EXECUTED (`bounds.txt`): a guest that opens 1,100 files
to write gets 1,024 and 76 `EMFILE` (33), then is cancelled; the walk makes exactly 1,024 writes
after the cancel (2,048 calls in all, `refused_total == 0`). So the bound is in calls and bytes,
not time, as the README says. If the owner answers 71 the other way ("a stop means stop"), the
change is small but is a specification change: `walk` would, for `"deadline"` and
`"cancelled"`, record each dirty buffer (a new `cause`) instead of writing it, and acceptance 5's
two rows change. The lane should hold the landing until 71 is answered, as the specification and
the pre-build review recommend.

### F6 — Info. Smaller notes

- **Owed buffers follow later renames (the builder's choice) with no check.** EXECUTED: M8 (the
  owed map left out of `_follow`) fails nothing. INFERRED: it is reachable only when an embedder
  clears its own `cancel` after a refused close, since the deadline and the limit refuse every
  later provider call. Agreed as built; a check is optional.
- **`_write_back` copies the buffer before the gate** (`mounts.py:909`), so a close or sync the
  gate refuses still makes one transient copy. Harmless; copying after `_gate` would be tidier.
- **The README's walk bound** says "1 GiB by default, the `memory_bytes` bound" but not "4 GiB
  when it is `None`", which Decision 8 states. One clause.
- **The Linux evidence's provenance.** The landing notes' Linux rows ran in a `python:3.13-slim`
  container (not pinned by digest) with a pytest stand-in; the wasmtime wheel there matches
  `uv.lock` (EXECUTED, SHA-256 `263b924576d9…`). It is evidence, not a build input, so §4.2 does not
  bind it; the release dry run's Linux and Windows `verify` jobs remain the authoritative run,
  and the lane's. Record the image digest next time.
- **The deadline seam** in `test_writes_land_at_every_ending` (the door sets
  `runner._stack()[-1].stop_at` to the ticker's count) is sound: the deadline is still named by the
  epoch callback, by count, on both sides of the comparison, as `tests/harness/files.py` already
  uses `_stack()`. Its `deadline_s=600` is a ceiling, not an assertion, so §4.9 holds; if the seam
  ever broke, the row would hang for ten minutes rather than fail fast.
- **Rebase.** See *The judge*: three files conflict with main.

## The implementer's choices where the specification was silent

1. **Names ending in `/`, `.` or `..` decided by one `stat`, answered as Linux.** Agreed. The
   answers follow cap-primitives' own reading (READ, `via_parent/open_parent.rs:40-55`: a
   trailing `/` or `/.` means "this folder", so `rmdir("d/")` is `rmdir(".")`, `EINVAL`), and
   the 228 raw rows agree on macOS (EXECUTED, the judge) and in the builder's Linux container
   (READ, its notes). The destination's ignored trailing `/` changes when 048 lands (F3).
2. **`path_create_directory(fd, "")` as the probe for "may wasmtime's folder be written".**
   Agreed; it is side-effect-free on every host. READ: `p1.rs:2038-2050` reads the descriptor
   (`get_dir_fd`, so a file is `EBADF` or `ENOTDIR`) and the empty string;
   `filesystem.rs:852-855` answers `NotPermitted` for a read-only folder before any path work;
   then `via_parent/create_dir.rs` strips trailing slashes and calls `open_parent`, whose
   `split_parent("")` returns `None`, which is `ENOENT` **before any system call**. Both the
   rustix build (`rustix/fs/mod.rs:49`) and the Windows build (`windows/fs/mod.rs:29`) use this
   same `via_parent::create_dir`. An empty name cannot create anything. EXECUTED: the builder's
   `probe2-{darwin,linux}.json` show 44 on writable folders, 63 on read-only ones, 8 on a file,
   with the tree unchanged; my `escape.txt` shows the host trees unchanged after every rename
   across. It fails safe: if a later wasmtime answered differently, a rename to a read-only side
   would answer `EXDEV` instead of `EPERM`, still a refusal with nothing forwarded. M3
   (the probe always "writable") fails seven checks (EXECUTED).
3. **A link with the follow flag is `EINVAL` once the paths are read.** Agreed; parity rows pass.
4. **An empty write changes nothing and leaves the buffer clean.** Agreed.
5. **An offset at or above `2**63` is `EINVAL` before the mode and the bound; ignored on an append
   descriptor.** Agreed; it matches Decision 4's order and the rows.
6. **The open mode as wasmtime keeps it** (no `FD_READ`: reads `EBADF`; `fd_filestat_set_size` on a
   descriptor that may not write `EINVAL`; `fd_sync` 0). Agreed; M15 and M16 fail the parity rows
   (EXECUTED).
7. **Set-times through a path accepted with no call even for a missing path.** Agreed (Linux's
   answer, per system in the table).
8. **`FileFault.path` for a rename is its `src`.** Agreed.
9. **Owed buffers follow later renames and removals.** Agreed (POSIX: the bytes are the file's);
   unchecked, and nearly unreachable (F6).

## Security, against the threat model

The adversary is the guest (threat model §2). The provider is the embedder's code and is judged
for robustness only. Each question the brief asked:

- **Can a guest with a writable mount write outside the provider: to the placeholder, a grant,
  the host?** No, by everything I tried.
  - Every write-shaped call on a number of the mount table is served (READ: each `_fd_*` and
    `_path_*` shadow forwards only when the number is not in the table, or for the preopen's
    read-only-safe calls). The placeholder stays a read-only preopen
    (`_Preopen(..., False)`, unchanged), so any forward that reaches it meets wasmtime's `EPERM`.
    Acceptance 10 checks the placeholder is empty during a run and gone after (EXECUTED, the
    judge).
  - Renames and links across: `EXDEV` or `EPERM`, nothing forwarded but the three
    side-effect-free probes (F3, choice 2; EXECUTED, `escape.txt`, host trees unchanged).
  - Symlinks within a mount: `ENOTSUP` (EXECUTED). No link can exist in a provider, so no path the
    runner resolves can lead elsewhere.
  - A write-back's path is always a normalized path that passed `_resolve` at open or a later
    rename's `dst`. A descriptor's path changes only through `_follow`, to `dst + suffix`; `dst`
    is never at or under a nested preopen (`_resolve`'s `EPERM`) nor strictly above one
    (`_above`'s `EBUSY`), so a descriptor can never come to name a grant's or the zip's path
    (READ). Acceptance 10 checks the guards (EXECUTED; each guard removed fails it, `guards.txt`).
  - The runtime's files: `/usr/local/lib/x`, `/usr/./local/lib/x` 63; `rmdir /usr` 10 (the judge);
    rename to the zip 63 (`escape.txt`); with `root=True`, to `/tmp/x` and `/x` 75 and to
    `/usr/local/lib/x` 63 (`escape.txt`).
- **Can it exhaust host memory, or time after its deadline?** Memory: bounded by the staging
  bound on growth (M14 and the growth-bound guard fail `test_writes_are_bounded`), owed buffers
  count (the reserved-number guard fails acceptance 16), with F4's transient doubling and
  one-eighth over-allocation. Time: the walk is bounded at 1,024 writes and the staging bound in
  bytes (EXECUTED, `bounds.txt`: 1,024 writes after a cancel, never more), each call the
  provider's own time (F5, question 71). The buffer calls are host fills of up to the bound with
  no fuel, bounded per call by the bound and over the run by the deadline, the class Decision 10
  names. Write amplification (up to `max_file_calls` × the bound handed to the provider) is
  documented and is the provider's to quota.
- **Can it make `run()` raise through provider answers in the write half?** No, as built
  (EXECUTED, `hostile_write.txt`, 45 of 45); but no check holds it (F2). A provider's
  `BaseException` is raised, by design, and stops the walk (the judge, acceptance 7).
- **Can it confuse descriptor tracking across rename, unlink, renumber?** Not as built.
  `fd_renumber` onto or from any provider number is `ENOTSUP` (032, unchanged). Owed buffers live
  in their own map, out of `table` (so `_entry` never finds them; a call on the number is
  forwarded and is wasmtime's `EBADF`) and out of `free` (so no open reuses it), and keep their
  count and bytes (READ `_fd_close`; the reserved-number guard fails acceptance 16). Renames and
  removals unlink what they replace and move what they rename (READ `_follow`); an unlinked
  folder answers `ENOENT` to every relative call and lists only its dots (the guard fails three
  checks). Two of these rules have no check (F1).
- **Cross-run state and `HOME`.** A mount at `/tmp`, writable or not, makes no `HOME`
  (READ `_home_folder:1648`); the README names the cross-run hazard with modules and data files.
- **Ctrl-C, the exit hook, a raising call.** No walk (each guard fails its check, `guards.txt`).
  The exit-hook check runs in a child process, which matters: `_hook["exiting"]` is process-wide
  and would disable every later walk in the judge's own process (READ).

## Each Decision against the code

1. **Nothing writable unless asked.** Holds (READ `Mount`, `_check_mounts`, `_Files.__init__`'s
   `mount.writable is True`; M10, M11, M18 and the writable-check guard each fail checks).
2. **The write half's protocol.** Holds as built (EXECUTED, `hostile_write.txt`); unguarded (F2).
3. **The open table.** Holds (READ `_open_writing`: top to bottom, at most two calls, the create
   by `write(path, b"")`, every buffer clean; M20 and the create-at-open guard fail checks).
4. **The buffer.** Holds (READ `_writes`, `_fd_filestat_set_size`, `_fits`); the order of checks
   is as stated; F4 on the memory it takes.
5. **Write-back at close and sync; owed buffers.** Holds (READ; M7, M12 and the reserved-number
   guard fail checks).
6. **The namespace calls.** Holds (READ `_namespace`, `_path_rename`, `_above`, `_across`; M3,
   M4, M9 and four guards fail checks). Composition with 048 (F3).
7. **Descriptors follow the guest's own changes.** Holds as built; the "only after success" rule is
   unguarded (F1).
8. **Write-back at every ending.** Holds (READ `walk`, `_instance:1772-1775`: after `_fuel_used`,
   inside the `try`, before `store.close()` and `table.record()`; five guards fail checks). The
   "not unlinked" rule is unguarded (F1). Question 71 (F5).
9. **Links and times.** Holds (the judge, acceptance 11).
10. **Limits and costs.** Holds; F4.
11. **The record.** Holds (READ; the `refused_total` guard fails its check). The judge change is
    the five literals named, each only gaining zeros (READ the diff).
12. **Parity with a writable grant.** Holds on macOS (EXECUTED, the judge: 228 raw rows, 39 v1.4
    rows); Linux per the builder's container (READ); Windows not run (the lane's dry run).
13. **Safety.** Holds (the security section).
14. **Docs.** Holds, with F6's missing "4 GiB" clause.

## Mutants

Mine (EXECUTED, `mutants.txt` and `mutants2.txt`; each alone, the four mount test files, 224
checks; restored and hashed after each, `git status` clean):

| mutant | checks failing |
|---|---|
| M1 `_made` judges `Errno` by `isinstance` | **none** (F2) |
| M2 `_made`: any falsy answer is success | **none** (F2) |
| M3 `_wasmtime_writable` always true | 7, among them acceptance 2, 10, 11 and 3 |
| M4 a rename of the mount itself reaches the provider | `test_raw_write_calls_answer_as_a_writable_grant_does` |
| M5 a rename's descriptors follow even when it is refused | **none** (F1) |
| M6 the walk writes back unlinked files | **none** (F1) |
| M7 the write half is not gated (cancel, deadline, limit) | `test_a_close_stopped_by_a_cancel_is_owed` |
| M8 owed buffers do not follow renames | **none** (F6; nearly unreachable) |
| M9 `_across`: a read-only mount side is not `EPERM` | 4, among them `test_a_writable_mount_is_asked_for` |
| M10 `_namespace`: no writable check | 4, the same |
| M11 `_path_open`: no writable check | 4, the same |
| M12 a close writes back an unlinked file | 6, among them acceptance 2, 9 and 3 |
| M14 `_fits` ignores the other staged bytes | `test_writes_are_bounded` |
| M15 a read-only descriptor writes into its buffer | 4, among them acceptance 2 and 3 |
| M16 a read-only descriptor can set its size | `test_raw_write_calls_answer_as_a_writable_grant_does` |
| M18 `_check_mounts` asks only the read half | 6 rows of `test_a_writable_mount_is_checked_before_any_work` |
| M20 `"x"` does not refuse an existing file | 3, among them acceptance 2 and 3 |

The specification's fifteen guards, re-run by me with the implementer's script (EXECUTED,
`guards.txt`), each fail exactly the checks the landing notes name: the writable check, the create
at open, the growth bound, the dst-inside-src rule, the `EBUSY` rule, the rule across (`EXDEV` and
`EPERM`), the unlinking of file descriptors, the unlinked-folder rule, the reserved number, the
fault catch in the walk, the limit in the walk, the skip when the call raises, the skip at the exit
hook, and `refused_total`. Restored byte for byte (`a6a0ed929a86`, `620389e3ab9d`).

## Acceptance criteria against evidence

Each named check passed in my judge run (EXECUTED, `judge.log`); "seen failing" is the
landing notes' for the new checks and mine (`guards.txt`) for the guards.

1. `test_a_writable_mount_serves_writes` — met (EXECUTED).
2. `test_a_writable_mount_answers_as_a_writable_grant_does` — met on macOS (EXECUTED); Linux in the
   builder's container (READ); Windows at the lane's dry run.
3. `test_raw_write_calls_answer_as_a_writable_grant_does` — met on macOS (EXECUTED); same note;
   three rows change when 048 lands (F3).
4. `test_refused_writes_are_recorded_on_exit_0` — met (EXECUTED).
5. `test_writes_land_at_every_ending` — met (EXECUTED); its deadline seam is sound (F6). It does not
   cover an unlinked file at the ending (F1).
6. `test_a_failed_write_back_at_the_ending_is_recorded` — met (EXECUTED).
7. `test_a_call_that_raises_writes_nothing_back` and `test_a_stopped_host_gets_no_write_back` — met
   (EXECUTED); both guards fail them (`guards.txt`). Acceptance 7's hostile-answer table lacks the
   write half (F2).
8. `test_a_writable_mount_is_asked_for` and `test_a_writable_mount_is_checked_before_any_work` —
   met (EXECUTED); M9, M10, M11, M18 fail them.
9. `test_open_files_follow_the_guests_renames_and_removals` and
   `test_an_unlinked_folder_holds_nothing` — met (EXECUTED); a refused rename is not covered (F1).
10. `test_a_writable_root_mount_keeps_the_runtime_and_other_grants` — met (EXECUTED); four guards
    fail it.
11. `test_links_and_times_in_a_writable_mount` — met (EXECUTED).
12. `test_writes_are_bounded` and `test_the_walk_is_bounded_and_keeps_its_record` — met
    (EXECUTED); their guards fail them.
13. 032's checks pass with only the five literals changed — met (EXECUTED; READ the diff); ratchet
    `grew 0`.
14. Judge green, lost 0, grew 0, ruff clean — met (EXECUTED). `--accept-judge` and the release dry
    run are the lane's.
15. This review: the guards re-run (`guards.txt`), plus seventeen mutants and the probes above.
16. `test_a_close_stopped_by_a_cancel_is_owed` — met (EXECUTED); the reserved-number guard and M7
    fail it.

## Constitution checks

- **§4.4, two channels:** holds. No import, shadow or forward is added; the 29 shadows serve the
  write half (READ). The one new forward, `path_create_directory(fd, "")`, is a probe on wasmtime's own
  numbers beside 032's two, side-effect free (choice 2).
- **§4.5, embedder-neutral:** holds. EXECUTED, `grep -i vfs` of the diff's added lines in `src/`,
  `tests/`, `README.md`, `CHANGELOG.md`: none.
- **§4.9, tests count:** holds. EXECUTED, grep of the test diff for `sleep`, `perf_counter`,
  `monotonic`, `time.time`: none; one `deadline_s=600` ceiling (F6).
- **§4.10, claims carry evidence:** holds in the landing notes; their numbers reproduce.
- **§4.13, tooling:** ruff clean; `pyproject.toml` untouched.
- **§4.15, safe by default:** holds. `writable` defaults to `False`; a call with no mounts is
  unchanged (acceptance 13); no default loosened. What `deadline_s` means for a mounted run is
  question 71 (F5).
- **§5.6 and §5.7:** not build-class (no `scripts/`, `recipes/`, `SHA256SUMS` or workflow). The
  judge changed (Decision 11 and the harness), so the lane needs `--accept-judge`; the branch must
  be rebased (three conflicts).
- **AGENTS.md rule 4:** the judge change is the one Decision 11 names; no check was weakened (READ
  the five literals; each gains keys).

## Disposition (filled in by the author, then confirmed by the reviewer)

## Verdict

**Not yet, but close.** The write channel is sound: nothing I tried reached the placeholder, a
grant, the zip or the host through a writable mount, every guard the specification names fails
its check when removed, and the judge is green with the landing notes' numbers. What is missing
is in the judge, not the code: two of Decision 7 and 8's rules (the walk skips unlinked files;
descriptors follow only a rename that succeeded) and the write half's type-judged answers are
kept but unguarded (F1, F2), and a mutant of each passes all 224 checks. Add those checks, seen
failing on M5, M6, M1 and M2. Answer F3 with the lane (which of 034 and 048 lands second, and the
served rename's trailing-slash rule). F4 to F6 can be fixed or answered in writing. A short
confirmation of the new checks is enough; no full re-review. The landing also waits on the
owner's answer to question 71 (F5), on the rebase onto main, and on the lane's `--accept-judge`
and release dry run.

## One line

A guest still cannot get out of a writable mount, and the code keeps every rule; but three of those rules (no write-back of an unlinked file at the ending, follow only a successful rename, answers judged by type) have no check, so add them, settle the 048 rename rule, and it lands after question 71.

## The implementer's Disposition (copied by the lane from the scratchpad)

## Disposition (filled in by the author, then confirmed by the reviewer)

By the implementer, 2026-10-18. The branch is rebased onto main `3a9588f`. The reviewed commits
are now `b947e5c` (was `bb354ba`), `be8ae7d` (`2fcfbee`), `fd3ff39` (`7588daa`) and `e214318`
(`7bad2d3`). The revision is `40515d3`. The three conflicts you named, plus
`tests/unit/test_runner_grants.py`, were each two appends at one place, resolved by keeping both.
Main's `mounts.py` change (reads near `2**63` as Linux answers them) merged cleanly beside
`_reads`' `readable` check. Each finding's answer is in the specification's Landing notes, last
part ("Revised 2026-10-18 against the build review"). The new checks were written first and
pass on the built code, as F1 and F2 expected. Each was seen failing on its mutant, applied one
at a time and restored byte for byte (`build/mutants-f1f2.log`). All are EXECUTED, frozen set
`build/sets/s-0cdc7b2bd78db6f5`.

1. **F1 — fixed (two checks).**
   - `test_unlinked_files_are_not_written_back_at_the_ending` (v1.4, both binaries) runs your
     scenario A with two endings, `os._exit(0)` and a cancel through the door. The provider's log
     is exactly `rename("/b.txt", "/a.txt")`, `write("/t", b"")`, `remove("/t")`. `/a.txt`
     holds `b"b\n"`, `/t` is gone, and nothing is refused. M6 fails it, both binaries.
   - `test_a_refused_rename_or_removal_moves_no_descriptor` (unit) runs your scenario B with a
     `dst` descriptor too. After a refused rename, the `src` descriptor writes back to `/a.txt`
     and the `dst` one to `/b.txt`. A refused `remove` unlinks nothing. A refused `rmdir` leaves
     the folder descriptor asking the provider. M5 fails it, and so does M5b (a removal unlinks
     even when refused).
2. **F2 — fixed (one check).** `test_a_write_half_fault_never_escapes` (v1.2, both binaries)
   uses five hostile answers: a fake `Errno` of 0, a fake `Errno` past i32, `0`, a coroutine, and
   an exception whose type's name raises. Each is answered at four places: a create at open, a
   close, a `mkdir`, and the walk. The results:
   - the guest gets 15 `EIO`s;
   - there are 20 faults, each with its text;
   - there are 20 `RefusedWrite(…, Errno.EIO, at, "fault")`, each holding a real `Errno`;
   - `run` raises nothing, and no "never awaited" warning appears.

   M1 and M2 each fail it, both binaries.
3. **F3 — answered in writing; the served rename is made ready.** 048 lands first, so 048's rule
   is not implemented here.
   - Which trailing `/` makes a served rename need a folder source is now one constant,
     `mounts.RENAME_SLASH_NEEDS_FOLDER = (True, False)`: the source's slash, the destination's
     slash. `_path_rename` reads it: one `stat` of the source, then `ENOTDIR` unless it is a
     folder.
   - After the rebase onto 048, exactly these change:
     - The constant becomes `(True, True)`.
     - `_path_rename`'s branch for two wasmtime numbers calls 048's `self._rename(...)`. It is
       034's only rename forward; `_across` forwards none.
     - `_write_sides`' grant side becomes 048's writable `files.Guarded`.
     - The raw rows `'a.txt' → 'newname/'`, `'a.txt' → 'b.txt/'` and `'a.txt' → 'a.txt/'` become
       54 on both sides on every host, and move to `WASMTIME_ROWS`.
     - `'d' → 'f/'` stays 0. 048's notes list it among the rows that become `ENOTDIR`, but `d`
       is a folder, so 49.0.3 renames it.
   - The served rename already answers those rows in the guard's order: the stat first, then
     `ENOTDIR`.
   - Nothing of 048's padding, `forward(..., stat=True)`, `PRIVATE`, `_zeroed`, or its rule that
     `files` is `None` without mounts is touched. `walk()` does nothing on a guard table.
4. **F4 — fixed and documented.**
   - Growth now uses `_grow`, which appends from one shared 64 KiB zero block, so it makes no
     temporary of the gap's size. Growing a buffer to 64 MiB peaks at 1.014 times the size under
     `tracemalloc`; the review measured 2.00.
   - `held` still counts a buffer's length. The README now says the host may hold up to about an
     eighth more (`bytearray`'s over-allocation), plus the one transient copy at a write-back.
5. **F5 — unchanged.** The build keeps Decision 8's answer. 034 waits on the owner's answer to
   question 71.
6. **F6 — fixed where it asked for a change.**
   - The README's walk bound now reads "1 GiB by default, 4 GiB when it is `None`".
   - `_write_back` copies the buffer only after the gate lets the call through.
   - The Linux image's digest is recorded:
     `python:3.13-slim@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b`.
     In it, on the revised tree, these passed:
     - the raw write rows and the write differences;
     - 032's `test_raw_calls_answer_as_a_grant_does`, which passes on Linux since main's fix;
     - the new F1 v1.4 check, the v1.4 write parity and the endings check (the snapshot).
   - No check is added for owed buffers following renames; you agreed it is nearly unreachable.
   - The deadline seam needs no change.

**The fifteen guards**, re-run on the revised source (`mounts.py` `4f643905fc0e…`, `runner.py`
`620389e3ab9d…`), each fail the checks the Landing notes name (`build/guards-revised.log`).

**The judge:**

```
wasi_python v1: 238/249 pass · 0 gap · 11 blocked · 0 fail (unit suite 831/839, 8 skipped)
ratchet vs 947036ec8d: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 22 · grew 0
1069 passed, 19 skipped
```

`ruff check` and `ruff format --check` are clean.

## Confirmation (2026-10-18)

By the reviewer, on `40515d3`, the revision on the rebased branch (`b947e5c`, `be8ae7d`, `fd3ff39`,
`e214318` on main `3a9588f`), in the worktree `../wasi_python-034`. I read the Disposition and the
revision's diff (`git diff e214318 40515d3`). Nothing in any repository tree was edited. Scripts
and outputs are in the same scratch folder (`rv034/`): `judge2.log`, `mutants_r.txt`,
`mutants_r7b.txt`, `guards_r.txt`, `bounds_r.txt`, `slash_rows_r.txt`, `gate_probe.txt`. Probes ran
on `git archive 40515d3` copies (`src034r/`, checked by `__file__`), so the worktree was never
touched by them. After every mutant and guard run, `git status` in the worktree was clean and
`mounts.py` hashed `4f643905fc0e…`, `runner.py` `620389e3ab9d…`. Each claim is EXECUTED or READ.

**The rebase (EXECUTED).** The lines `987012e..7bad2d3` changes in `src/` and `README.md` are
identical to the lines `3a9588f..e214318` changes. The test diffs hold the same lines once sorted.
So the conflicts were resolved by keeping both sides, as the Disposition says.

**The judge (EXECUTED, `judge2.log`, set `s-0cdc7b2bd78db6f5`, no flags, exit 0):**

```
wasi_python v1: 238/249 pass · 0 gap · 11 blocked · 0 fail   (unit suite 831/839, 8 skipped)
ratchet vs 947036ec8d: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 22 · grew 0 · judge changed: …
1069 passed, 19 skipped
```

`ruff check`: all checks passed. `ruff format --check`: 62 files already formatted. These are the
Disposition's numbers.

**Each finding against its fix.**

1. **F1: fixed (EXECUTED).** Mutants re-run on the revision, each alone, over the four mount test
   files (234 checks): M6 (the walk writes back unlinked files) now fails 2 checks, both binaries of
   `test_unlinked_files_are_not_written_back_at_the_ending`. M5 (a rename's descriptors follow when
   it is refused) fails 1, `test_a_refused_rename_or_removal_moves_no_descriptor`. My extra M5b (a
   refused removal unlinks) fails the same check. READ: the v1.4 check is my scenario A with two
   endings (`os._exit`, a cancel), and it asserts the provider's whole log. The unit check covers a
   `src` descriptor, a `dst` descriptor, a refused `remove` and a refused `rmdir`.
2. **F2: fixed (EXECUTED).** M1 (`isinstance` in `_made`) and M2 (any falsy answer is success) each
   now fail 2 checks, both binaries of `test_a_write_half_fault_never_escapes`. READ: it covers the
   create at open, the close, `mkdir` and the walk. It also asserts `type(r.errno) is Errno` for
   every record, and no "never awaited" warning.
3. **F3: answered, and the switch is right (EXECUTED, `slash_rows_r.txt`).**
   - With `RENAME_SLASH_NEEDS_FOLDER = (True, False)` as committed, the mount answers as today's
     grant on all seven trailing-slash rows I ran.
   - On a copy with `(True, True)`, the mount answers 54, with one `stat` and no `rename`, on the
     three rows that rename a file to a name ending in `/` (`'a.txt' → 'newname/'`,
     `'a.txt' → 'b.txt/'`, `'a.txt' → 'a.txt/'`).
   - On that copy `'d' → 'f/'` stays 0, because `d` is a folder; the Disposition is right on that
     row. `'a.txt/' → 'c'` stays 54, and `'missing' → 'x/'` stays 44.
   - READ: `_path_rename`'s branch for two wasmtime numbers is still its only rename forward, and
     `_across` forwards none.

   The list of what changes when this is rebased onto 048 (the constant, the forward branch, the
   grant side of the parity, the three rows into `WASMTIME_ROWS`) is complete as far as I can see
   from 034's side. Whether 048 is built as its spec says is that spec's own build review.
4. **F4: fixed (EXECUTED, `bounds_r.txt`).**
   - Growing a buffer to 64 MiB by `fd_filestat_set_size`, and by a `pwrite` past the end, now
     peaks at 1.01 times the size (it was 2.00) and holds 1.01 times after.
   - The table's `staged` count is exactly 64 MiB.
   - The walk bound is unchanged: 1,024 descriptors, 76 `EMFILE`, 1,024 walk writes after a cancel.
   - READ: `_grow` appends slices of one shared 64 KiB block. The README states the eighth and the
     one transient copy.
5. **F5: unchanged, as answered.** 034 waits on question 71.
6. **F6: fixed where it asked (READ).**
   - The README now says 4 GiB when `memory_bytes` is `None`.
   - `_write_back` calls `_gate` before it copies the buffer.
   - The container image's digest is recorded.

**One new gap, which the revision exposed (EXECUTED).**

- Before the revision, `_write_back` went through `_change`. So my M7 (`_change` without `_gate`)
  failed acceptance 16 through the close.
- `_write_back` now calls `_gate` itself, which is right. Removing that call (M7b) still fails
  `test_a_close_stopped_by_a_cancel_is_owed`.
- But M7 now **passes all 234 checks**. Nothing checks that a create at open or a namespace call
  (`mkdir`, `remove`, `rmdir`, `rename`) is refused by the cancel, the deadline and the file-call
  limit. That was already unchecked before the revision; the close's coverage hid it.
- What M7 would let through (EXECUTED, `gate_probe.txt`, 50 `mkdir`s with `max_file_calls=5`):
  - as built: 5 provider calls, and the run ends `"out of file calls"`;
  - under M7: 50 provider calls, and the run exits 0.

  So decision 42's bound, which Decision 10 extends to the write half, is kept by the code but not
  held by any check.

**N1, the one condition.** Add a check, seen failing on M7. A guest makes `mkdir`s, or writing
opens, past `max_file_calls`. The provider sees exactly the limit's count, and the run ends
`"out of file calls"`. The same after a cancel the provider sets (one row is enough, as in
acceptance 16): a `mkdir` answers `ECANCELED` with no provider call. The lane can confirm the
check fails on M7 and passes on the built code; it needs no further review.

**Everything else re-run on the revision (EXECUTED).**
- Every other mutant of mine is still caught: M3, M4, M9, M10, M11, M12, M14, M15, M16, M18 and
  M20.
- M8 (owed buffers do not follow renames) still survives, as agreed (F6).
- The spec's fifteen guards, removed one at a time with the implementer's script (`guards_r.txt`),
  each fail the checks the landing notes name.

**Result: 034 lands once N1's check is added and seen failing on M7.** The landing also needs:
- the owner's answer to question 71;
- 048 landing first, then 034 rebased onto it as the Disposition's F3 describes;
- the lane's `--accept-judge` (the judge changed) and the release dry run, with Windows still not
  run.

One line: F1 to F6 are fixed or answered and their checks catch their mutants; one more check is
needed, because the write half's cancel, deadline and file-call-limit gate on creates and namespace
calls is still unguarded.

## Confirmation of the rebase (2026-10-18)

By the reviewer, on `eb70481`. The branch is rebased onto main `77bd08e`, which carries specs 048
and 036, and its last two commits are `9822812` (the composition and N1) and `eb70481`. Outputs are
in `rv034/`: `judge3.log` and `mutants_rb.txt`. Each claim is EXECUTED or READ.

- **The judge (EXECUTED, set `s-0cdc7b2bd78db6f5`, no flags, exit 0).**
  - Result: `258/269 pass · 0 gap · 11 blocked · 0 fail`; `ratchet vs 361775dd62: lost 0 · …
    gained 22 · grew 0`; `1132 passed, 19 skipped`.
  - `ruff check` and `ruff format --check` are clean.
- **The forwarded rename holds 048's rule (READ).**
  - `_path_rename`'s branch for two wasmtime numbers calls `self._rename(...)`, as main's
    `_path_rename` does.
  - 048's `_rename` is byte-identical to main's.
  - `fd_readdir`'s forward branch, which carries 048's zeroing, is unchanged.
  - `_across` still forwards no rename and no link.
  - Every line the branch removes from main's `mounts.py` is 032's read-only text that 034
    replaces. None is 048's.
- **The served rename holds 048's rule (READ).** `RENAME_SLASH_NEEDS_FOLDER = (True, True)`. A
  trailing `/` on either path makes one `stat` of the source, and the answer is `ENOTDIR` unless the
  source is a folder. The provider is given the plain normalized names. A mount has no links, so
  this rule is there for parity only, not for safety.
- **Nothing of 048's checks was weakened (READ).**
  - The only lines the branch removes from main's tests are 032's three-key `calls` literals and
    032's harness provider, which 034 rewrites.
  - One more line is 048's `test_a_guard_call_leaves_the_other_calls_native`. Its
    `g.table.record().calls == {three zero keys}` becomes `dict.fromkeys(...)` over all eight keys.
    That adds keys and drops nothing.
  - In `runner.py`, a guard table's `walk()` does nothing, and `files` stays `None` without mounts
    (`files = table.record() if mounts else None`).
- **Mutants on the rebased tree (EXECUTED).** Each was applied alone over the four mount test files
  plus `test_rules.py` and `test_runner_tools.py` (321 checks), then restored byte for byte.
  - **R1**, the constant back to `(True, False)`: fails
    `test_raw_write_calls_answer_as_a_writable_grant_does`.
  - **R2**, the pair branch forwarding the rename unchanged, as on 49.0.0: fails 6. These are
    048's `test_a_trailing_slash_rename_rule`,
    `test_a_trailing_slash_symlink_rename_cannot_escape[grant, root]`,
    `test_the_rename_is_forwarded_by_its_plain_names` and
    `test_a_call_without_mounts_is_unchanged_but_for_the_two_fixes`, plus 034's raw write rows.
  - **M7**, `_change` without `_gate`: fails `test_the_write_half_is_gated`.
- **N1 is met (READ, and M7 above).** `test_the_write_half_is_gated` covers `mkdir`s and writing
  opens past `max_file_calls=5`: exactly 5 provider calls, and the run ends `"out of file calls"`.
  It also covers a cancel set inside a provider's `stat`, after which a `mkdir`, a `rename` and a
  create at open each answer `ECANCELED` (11) with no provider call and no refusal recorded.
- **A process note.** My first try at these three mutants started the whole mutant list, and I
  stopped it part-way. That left my own R1 edit (one line, the constant) in `mounts.py`. I restored
  the file from `HEAD`'s bytes; `git status` was clean and `mounts.py` hashed `492bf04ce88b…`
  before the rerun and after it.

**Result: the rebase is confirmed, and N1 is met.** On 034's side, nothing remains but the owner's
answer to question 71 and the lane's `--accept-judge` and release dry run. Windows has still not
been run.

One line: both renames hold 048's rule, none of 048's checks lost an assertion, and N1's check
catches M7.
