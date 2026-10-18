# Review of 048 — The sandbox holds on wasmtime 49.0.0 (the build; a security change)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification,
  its pre-build review or its confirmation. I read `AGENTS.md`, the constitution, specification
  048 with its landing notes, its pre-build review with the Disposition, the Confirmation (C1,
  C2, N1, N2) and the author's note (`048-the-sandbox-holds-on-wasmtime-49-0-0-spec-2026-10-18.md`),
  and the diff (`git show d085204`): all of `_rename`, `_source_type`, `_plain`, `_zero_padding`,
  `bind` and `forward` in `src/wasi_python/mounts.py`; `_instance`, `_drive`, `_shared`,
  `_guard_linker` and `_stat_trampoline_module` in `runner.py`; the new and changed checks;
  `README.md`, `SECURITY.md`, `CHANGELOG.md`. I read wasmtime v49.0.3 in
  `context/prior_art/wasmtime-v49` (`crates/wasi/src/p1.rs:1948-2035` `fd_readdir`,
  `p1.rs:2257-2273` `path_rename`, `crates/wasi/src/filesystem.rs:1078-1104` `rename_at`,
  `filesystem/primitives/via_parent/rename.rs`), the memo's `releases.txt`, and spec 034's
  `_path_rename`, `_fd_readdir`, `walk`, `_two_sides` and `_write_sides` on
  `spec/034-writable-mounts`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `d085204` on `spec/048-the-sandbox-holds` in the worktree
  `../wasi_python-048`, on main's `a45148c`. The files as reviewed: `mounts.py` SHA-256
  `f5f4372ddae3…`, `runner.py` `08a2e3a03e15…` (EXECUTED, `shasum`, equal to `git show HEAD:`).
- **Ran (EXECUTED, darwin-arm64, Darwin 25.5.0, `uv run`, wasmtime-py 49.0.0, the frozen set
  `build/sets/s-0cdc7b2bd78db6f5` read only).** Scripts and outputs are under
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/048-buildreview/`:
  - `judge-full.log`: `uv sync`, then `WASI_PYTHON_ARTIFACTS=… uv run pytest`, no flags. `uv run
    ruff check src tests recipes/guest` and `uv run ruff format --check src tests recipes/guest`.
  - `mutants/run_mutants.py` → `mutants/summary.txt`, `mutants/summary2.txt`, `mutants/M*.log`:
    fifteen one-line mutants, each applied alone to the worktree's `mounts.py` or `runner.py`
    (its text asserted to occur once), the eleven checks this change adds or touches run, the
    file written back and checked by SHA-256.
  - `probe/probe_used_namlen.py` → `.txt`: a guest `used` pointer over an entry's `d_namlen`.
  - `probe/probe_used_keep.py` → `.txt`: where criterion 3's `used` case can and cannot fail.
  - `probe/probe_race.py` → `.txt`: a folder swapped for an outward link between the guard's
    stat and its forward, on the build and with mutant M1 in process.
  - `probe/probe_order.py` → `.txt`: fifteen slash-named renames on today's linker and the guard's.
  - `probe/probe_real_leak.py`, `probe_real_leak2.py`: real wasmtime padding bytes, 200 rounds.
  Every grant was a folder under the scratch folder or a test's `tmp_path`. After every run
  `git status --short` in the worktree was empty and both hashes matched (EXECUTED).

## The judge

EXECUTED (`judge-full.log`, exit 0):

```
wasi_python v1: 220/231 pass · 0 gap · 11 blocked · 0 fail   (unit suite 817/825, 8 skipped)
ratchet vs c42410a127: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 4 · grew 0 · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_2_hostile_guest.py, tests/harness/files.py and 2 more
================= 1037 passed, 19 skipped in 234.69s (0:03:54) =================
```

Equal to the landing notes' scoreboard, line for line. Both ruff runs are clean ("All checks
passed!", "64 files already formatted"). **grew 0** is the suite-wide evidence that the guard
spends no guest fuel (every metered check that lists a folder now goes through it).

## Mutants (EXECUTED)

| mutant | caught by |
|---|---|
| M1 `_plain` returns the path (the slash is forwarded) | **nothing** (F2) |
| M2 the stat follows links (flag 1) | criterion 1 (both), criterion 2 |
| M3 no zeroing | criterion 3, 5b, criterion 6 (the parity) |
| M4 the walk ignores `used` (`keep = range(0)`) | **nothing** (F4) |
| M5 the target's slash is not tested | criterion 2, 5b |
| M6 C2 broken: an over-long slash path forwarded unchanged | criterion 2, 5b |
| M7 a stat error answers `ENOTDIR` | criterion 2, 5b |
| M8 the filetype read at byte 17 | criterion 2, criterion 4, 5b |
| M9 a cut-short header not zeroed | criterion 3 |
| M10 the stat forward keeps its allowance | criterion 4 |
| M11 the guard table is reported | 032's routing check, 5b |
| M12 the guard also shadows `fd_read` | criterion 5 |
| M13 a call without mounts on today's linker | criterion 1 (both), criterion 2, 032's routing check |
| M14 no UTF-8 decode before the stat | 5b |
| M15 the rule off (a plain forward) | criterion 1 (both), criterion 2, 5b |

M15 also confirms what the landing notes say of criterion 2 with the rule switched off. Their
citation is wrong, though: `build/seen-failing-2.log` ran seven tests and criterion 2 is not
among them (F6).

## Findings, most severe first

### F1 (medium). A guest can steer the padding walk past every entry but the first

**Evidence.** wasmtime writes the listing, then wiggle writes the returned count to `used`
(READ, `p1.rs:2011-2034`: `fd_readdir` returns `Size`, written after the body). If the guest
points `used` at `buf + 16`, the count lands on the first entry's `d_namlen`. `_zero_padding`
reads that field from the bytes after the overwrite (`pos += 24 + unpack_from("<I", data,
pos + 16)`). So it jumps by `24 + count` and stops. No later entry is zeroed. EXECUTED
(`probe_used_namlen.txt`):

- pure, a fake memory, padding `a5 a5 a5`, `used` at `buf + 16`:
  `[(0, 000000), (25, a5a5a5), (51, a5a5a5), (79, a5a5a5)]`;
- end to end on `Guarded`, wasmtime's forward then `0xA5` in each padding (offsets learnt from a
  listing with `used` outside), `used` at `DIRBUF + 16`:
  `[(0, 000000), (25, a5a5a5), (51, a5a5a5)]`, against all zeros with `used` outside.

`used` at `DIRBUF + 16` is 4-aligned, so wasmtime accepts it. wasmtime 49.0.2 writes zero
padding whatever `used` is (READ, `p1.rs:2010`, `vec![0; …]`). So the shadow does not do what
49.0.2 does, and Decision 4's "zeroes the three padding bytes after each entry" fails for a guest
that picks its own `used`. That is exactly the hostile guest the advisory is about.

I did not see real host bytes come through this way. In a fresh process 200 rounds over a
60-entry folder gave no non-zero padding, with or without other calls in between (EXECUTED,
`probe_real_leak*.py`). That matches the builder's 0 of 1,800. But 5b's seen-failing run did
show real bytes (`8b 1a 2f`, `70 2f 1f`). So in a long-lived embedder the leak is INFERRED to
come through.

**Fix.** The walk must not depend on bytes the `used` write may have replaced. One way: when
`used`'s 4 bytes overlap a `d_namlen` field the walk is about to read, learn the layout from a
second listing that wasmtime writes into the stat trampoline's own page. That page would get an
`fd_readdir` import, use the same `fd` and `cookie`, and take up to the page's size. The guard
then zeroes those offsets in the guest's buffer, skipping `used`. Another way: always list into
a private memory and copy the bytes out. That keeps 5b's trap rows only if the copy raises the
same traps. Either way, add criterion 3 cases with `used` at `buf + 16` and at a later entry's
`d_namlen`. Seen failing first: the probe above.

### F2 (medium). The plain-name forward, the half of the rename fix that closes the race, has no check

**Evidence.** Mutant M1 makes `_plain` return the path unchanged. Then a folder named `d/` is
forwarded *with* its slash. All eleven checks still pass (EXECUTED, `mutants/M1.log`). The
pre-build review's F1 asked for a unit check that the forwarded lengths carry no trailing `/`.
The Disposition carried that only as text ("in Decision 1's text and the Design line"). No
check was built (READ, the diff).

What it guards, EXECUTED (`probe_race.txt`). A wrapper around `_source_type` swaps the real
folder `d` for `d -> ../outside` right after the stat answers "folder". That is what a
concurrent call or another host process can do. Then `rename("d/", "stolen")`:

- the build: `errno 0`, the grant holds `['stolen']`, `stolen` is the link, `outside` is
  untouched;
- M1: `errno 0`, the grant holds `['d', 'stolen']`, `outside` no longer exists, and its canary
  is now inside the grant. That is the escape, on this macOS.

So the code is right today. But the judge would let the high-severity escape come back through
a one-line change. AGENTS.md rule 3 says a failure mode, once seen, becomes a check.

**Fix.** Add the probe as a unit check in `test_runner_mounts.py`: the swap after the stat, the
outside folder untouched, and the link itself renamed. Also add (or instead) the pre-build
review's lighter assertion: wrap `forward` and check that a forwarded `path_rename`'s two
lengths end in no `/` after the source passed. The race check is host-independent in what it
asserts. It is the only one that shows the effect on a following kernel.

### F3 (low). The errno order differs from both 49.0.0 and 49.0.3 more than the specification records

**Evidence.** In 49.0.3, `rename_at` refuses a read-only or mixed-permission pair with `EPERM`
before it touches a path (READ, `filesystem.rs:1084-1092`). `path_rename` checks both
descriptors before it reads either path (READ, `p1.rs:2265-2268`). Only then does
`via_parent/rename.rs` stat the source. The guard reads and decodes both paths and stats the
source before wasmtime sees the call. EXECUTED (`probe_order.txt`; native = today's linker,
guarded = the build):

| rename | native (and 49.0.3, READ) | guarded |
|---|---|---|
| `w.txt` → bad descriptor `x/` | `EBADF` | `ENOTDIR` |
| `w.txt/` → a file's descriptor | `EBADF` | `ENOTDIR` |
| `w.txt/` (writable) → read-only `x` | `EPERM` | `ENOTDIR` |
| `w.txt` (writable) → read-only `x/` | `EPERM` | `ENOTDIR` |
| `w.txt/` → bad descriptor, 5,000-byte target | `EBADF` | `ENAMETOOLONG` |

The other ten rows agree (a missing or non-UTF-8 path, `/`, `./`, an absolute path, a `..`
climb, a NUL). No row renames anything, so nothing here touches the sandbox. But Decision 1 says
the rule "only ever changes an answer where a writable place lets a rename happen at all
(elsewhere wasmtime answers `EPERM`/`EROFS`, except that a read-only missing source now reads as
its stat's error)". For the build that sentence is false. 5b's own rule table asserts
`"read-only file, slash": ENOTDIR` (native `EPERM`), which fixes the departure in the judge
without naming it. The spec's stated ordering difference covers only a bad parent of the target.

**Fix.** Either record it, or match it. To record it: amend Decision 3 and the landing notes to
say that, once a slash is seen, a bad descriptor, a read-only or mixed pair, or an over-long
path answers the guard's errno first (`ENOTDIR`/`ENAMETOOLONG`/the stat's) where 49.0.3
answers `EBADF`/`EPERM`. Then name the `"read-only file, slash"` row as that difference. To
match it: test both descriptors first, for example with a forwarded `fd_fdstat_get` on the
stat page, but that buys parity at the cost of more forwards. Recording it is enough.

### F4 (low). Criterion 3's `used`-inside case cannot fail

**Evidence.** The case puts `used` at `buf + 20`, over the first entry's `d_type` and padding.
The count is 80, so bytes 21-23 of `used` are already zero. A walk that zeroed them anyway
changes nothing there. Mutant M4 (`keep = range(0)`) passes every check (EXECUTED). With `used`
at `buf + 72`, the third entry's padding (the entry starts at 51; 72 is 4-aligned), the count's
low byte sits in the padding. M4 then reads back `0` where wasmtime wrote `80`; the build reads
`80` (EXECUTED, `probe_used_keep.txt`: build `{20: 80, 72: 80}`, M4 `{20: 80, 72: 0}`).

**Fix.** Move the case to an aligned `used` whose low byte falls in a padding byte (`buf + 72`
for the `d` listing, or compute it from the layout). Add F1's `buf + 16` case beside it.

### F5 (low). How 034 composes: two more things than the landing notes say

The notes name `_rename` in 034's forward branch, the served rename's slash answers, zeroed
listings, and keeping the stat trampoline. All four are right. Two more (READ,
`spec/034-writable-mounts`):

- **034's write parity still compares against an unguarded grant.**
  `test_raw_write_calls_answer_as_a_writable_grant_does` builds its grant side in `_write_sides`
  with `files.grant_raw`, which is today's linker, with no guard. Its rows include
  `("a.txt", "newname/")`, `("a.txt", "b.txt/")`, `("a.txt", "a.txt/")` and `("d", "f/")`. On
  wasmtime 49.0.0 a target slash is stripped, so a file renames to `newname`. 034's served
  rename matches that: it resolves the target's must-be-a-folder flag and drops it
  (`(dst, _) = …`; only `src_folder` is tested). After 048, a guarded grant answers `ENOTDIR` to
  each of those. So whichever lands second must do three things: move `_write_sides`' grant to a
  writable `Guarded`; make the served rename require a folder source when *either* path ends in
  `/`; and re-derive any of those rows in `LINUX_ROWS`/`WASMTIME_ROWS`, because the guard makes
  them the same on every host. Otherwise 034's parity holds a writable mount to the vulnerable
  reference.
- **Every call now has a table.** 034 adds `if table is not None: table.walk()` in `_instance`.
  After 048 that runs on every call. For a guard table it does nothing, because the table and
  `owed` are empty (INFERRED, from `walk`). It must still never be reported. Also, the
  `Mounted.entered` → `_OnStack` move in `tests/harness/files.py` will conflict textually with
  034's `Mounted` changes. And the README's mounts bullet is edited by both.

**Fix.** Add these to "How spec 034 must compose with this" so the second lander does not have
to find them.

### F6 (low). One citation in the landing notes is wrong

"With the guard plumbing built but its two fixes switched off … `build/seen-failing-2.log`: … and
criterion 2 failed as on today's code." That log ran seven tests and lists three failures:
criterion 3, 5b and the parity. Criterion 2 is not in it (READ; `grep -c trailing_slash` → 0).
The claim is true: mutant M15 shows it (EXECUTED). But the evidence it cites does not hold it.
Cite `build/seen-failing-rule-each.txt` (today's code) or re-run it, per §4.10.

### Notes (no change needed)

- **Criterion 3's injected `0xA5` (the implementer's question).** The specification's "Seen
  failing first: without the zeroing, the `0xFF` padding (or host bytes) survives" rests on a
  premise that does not hold. wasmtime writes all 24 header bytes from its own dirent buffer
  (READ, `p1.rs:2013-2019`), so the guest's `0xFF` never survives. On 49.0.0 those bytes are
  whatever its heap holds, which is mostly zero in a fresh process (EXECUTED, my probes).
  Writing `0xA5` into the padding right after the real forward does stand for "host bytes", and
  it is the only way the check can fail first every time. The check still pre-fills with `0xFF`
  and asserts zeros over `[buf, buf + used)` on full and cut-short buffers, as worded. 5b and
  criterion 6 keep wasmtime's real bytes. I read it as honest and within the wording's "(or
  host bytes)". The landing notes say so plainly.
- **The 4,096-byte limit on both paths (the implementer's question).** I accept it. It applies
  only once a slash is seen. A path without a slash of any length is forwarded as before. It
  bounds what the host copies. It is the condition C2 option the specification names, extended
  to the target for the reason the notes give. The only cost is the `EBADF` → `ENAMETOOLONG`
  ordering row in F3.
- **Decoding both paths before the stat (the implementer's question).** Right. wasmtime reads
  the source, then the target, before the rename (READ, `p1.rs:2267-2268`). The guard's
  `_path` → `_text` for the source and then the target gives the same `EILSEQ`. 5b's "not UTF-8,
  slash" row and my "not UTF-8 source, slash target" row agree with native (EXECUTED). M14 is
  caught.
- **`_rename`'s order and C2 (the implementer's question).** Here is the order. Test both paths'
  fit. Test either path's last byte. If a path does not fit, forward unchanged: wasmtime reads
  both strings before `rename_at`, so it cannot rename (READ, `p1.rs:2267-2271`). Then read,
  bound and decode both paths. Then stat the trimmed source on the private page. Then forward
  with trimmed lengths. Every exit after a slash is seen returns an errno or forwards trimmed
  lengths. C2 holds (M6 is caught; criterion 2's 4,202-byte `./…/s/` case gives `ENAMETOOLONG`
  and leaves `d` and `s` in place, EXECUTED).
- **Criterion 7's release lines (the implementer's question).** I accept them as major
  versions. All eleven tags in `releases.txt` are `M.0.P` or an `-rc` (READ). The predicate
  never lets a guard go on anything it cannot read (a minor bound, an open top, `~=`, `!=`).
  The fixed table matches C1's three examples and adds two more. The JSON lists are asserted
  equal to the check's. A guard that may go is enforced only by its advisory id disappearing
  from `mounts.py` and the tests. That is weak as a removal check. Criteria 1-3 would fail
  first if the code went while its checks stayed, so it is enough.
- **The two judge changes beyond the new checks (the implementer's question).**
  - Spec 032's `test_a_call_without_mounts_is_unchanged`. Decision 7 requires it to expect the
    guard linker. It still asserts `files is None`, the result, and the two-thread isolation.
    "Served" is narrowed to `{fd_readdir, path_rename}`, not widened. It is honest. Its name now
    overstates it, which is cosmetic.
  - The 032 parity's grant side through `Guarded`. 032's `_parity_script` has no slash-named
    rename row. So every rename row is forwarded unchanged. Every listing row is wasmtime's
    bytes with only the padding zeroed, which is 49.0.2's reference. The parity therefore still
    holds a mount to wasmtime's own answers in every byte but the padding. The "guard equals
    native" anchor is moved to 5b, which compares today's linker with the guard row by row,
    traps included. M3 is caught by both. That is no weakening for 032's rows. It becomes one
    the day a slash row is added to a parity whose grant side is `Guarded`, because F3's order
    rows then sit in the reference. So F3 should be recorded before 034 adds such rows.
- **Calls without mounts otherwise behave as before.** `Completed.files` is `None` (EXECUTED:
  5b's `run` and 032's check pass; M11 is caught). Only the two calls are shadowed (EXECUTED:
  criterion 5; M12 is caught). The fuel is unchanged (EXECUTED: criterion 4 at every cap, and
  the ratchet's grew 0). The file-call limit can never stop a call without mounts, because
  forwards never reach `_ask` (READ). EIO-after-stop and Ctrl-C at these two calls are new for
  plain calls, as Decision 7 says, and are stated in the CHANGELOG. `_instance` is the only
  place a guest is instantiated, so snapshot and plain calls both get the guard (READ, grep).

## Decisions against the build

| Decision | built as decided? | evidence |
|---|---|---|
| 1 the 49.0.3 rule, forwarded by plain names | yes; the plain-name half is unguarded (F2) | READ `_rename`, `_plain`; EXECUTED criterion 2, `probe_race.txt` |
| 2 the stat on a private one-page memory; C2 | yes | READ `stat_trampoline_wat`, `_source_type`; EXECUTED M2, M6, M8 caught |
| 3 the stat's errno; `ENOTDIR` only for a non-folder | yes; the recorded order difference is too narrow (F3) | EXECUTED criterion 2, 5b, `probe_order.txt` |
| 4 padding zeroed, `used` kept | not for a guest that aims `used` at a `d_namlen` (F1) | EXECUTED `probe_used_namlen.txt`, `probe_used_keep.txt` |
| 5 removal tied to the published floor (C1) | yes | READ `_guard_may_go`; EXECUTED criterion 7 passes |
| 6 `path_symlink` stays native | yes | READ, `GUARDED` holds two names; EXECUTED criterion 5 |
| 7 routing; the guard table never reported | yes | READ `_instance`; EXECUTED 5b, 032's check, M11 and M13 caught |

## Acceptance criteria against evidence

| # | check | result |
|---|---|---|
| 1 | `test_a_trailing_slash_symlink_rename_cannot_escape[grant]`, `[root]` | **met** (EXECUTED; fails under M2, M13, M15). The host probe only reports. Every grant and the private root's parent are under `tmp_path` (READ). |
| 2 | `test_a_trailing_slash_rename_rule` | **met** (EXECUTED; target-slash cases ran through CPython, N1; the C2 over-long case is there; fails under M2, M5-M8, M13, M15) |
| 3 | `test_a_grant_readdir_writes_zero_dirent_padding` | **met as worded, but its `used` case is vacuous** (F4) and it misses F1's case |
| 4 | `test_the_rename_rule_forward_is_fuel_neutral` | **met** (EXECUTED; fails under M8, M10) |
| 5 | `test_a_guard_call_leaves_the_other_calls_native` | **met** (EXECUTED; fails under M12) |
| 5b | `test_a_call_without_mounts_is_unchanged_but_for_the_two_fixes` | **met**; its rule table pins F3's read-only row without naming it |
| 6 | the raw parity with `DIRENT_MASKED = range(8, 16)` | **met** (EXECUTED; fails under M3). The grant side moved to `Guarded`, which is honest (Notes). |
| 7 | `test_the_rename_and_readdir_guard_match_the_floor` | **met** (EXECUTED; C1's three inputs plus two, the JSON lists, today's `>=49,<50` keeps both) |
| 8 | ruff, judge, ratchet | **met** (EXECUTED: 0 fail, lost 0, grew 0, gained 4; the lane accepts with `--accept-judge`, five judge files) |

## Constitution checks

- **§4.1 (patches temporary):** met. No upstream source is touched. Each guard has a removal
  rule tied to the published floor (criterion 7).
- **§4.4 (two channels):** met. The guest's imports are unchanged. The stat trampoline is a
  host-side module in the call's store. It imports one preview1 call and is never visible to
  the guest (READ).
- **§4.5 (embedder-neutral):** met. Nothing names an embedder.
- **§4.9 (tests count):** met. Every new check counts errnos, bytes, fuel or files. The race
  probe in F2 would too.
- **§4.10 (claims carry evidence):** met but for F6's citation.
- **§4.13 (tooling):** met. `uv` only, ruff clean, no dependency added (READ, no
  `pyproject.toml` change).
- **§4.14 (git):** met. One specification on its own `spec/` branch, not pushed. Not
  build-class, which is right: the diff touches only `src/`, `tests/` and three documents (READ,
  `git show --stat`).
- **§4.15 (safe by default):** met. It only tightens. A call given nothing still has nothing
  writable.
- **§6.1 (keep the wall whole):** met for the escape (criteria 1 and 2, EXECUTED). Not yet for
  the padding against a guest that picks `used` (F1). The race defence is right but unguarded
  (F2).

## Disposition (filled in by the author, then confirmed by the reviewer)

The implementer's answers. The branch was first rebased onto main's `b5b7869` (main had gained
one review file; no conflict). Everything below was EXECUTED in the worktree `wasi_python-048`
on darwin-arm64, wasmtime-py 49.0.0, the frozen set `s-0cdc7b2bd78db6f5`. The scratch plugins
named here live outside the repository (`scratchpad/plug048/`) and stand in for the code as
reviewed, or for a mutant, one at a time.

- **F1 (the walk trusted a `d_namlen` the guest's `used` can overwrite): fixed, the preferred
  way.** `_fd_readdir`'s forwarded branch now calls `_Files._zeroed`. When `used`'s 4 bytes lie
  outside `[buf, buf + count)`, only wasmtime has written the listing, and the walk
  (`_zero_pads`) reads it as before. When they lie over it, the guard lists the folder again on
  its own page, with the same descriptor, cookie and length. The guard trampoline now imports
  `PRIVATE = (path_filestat_get, fd_readdir)`, and its `(memory 1)` grows to the buffer length
  when needed. The guard zeroes that copy's padding and writes it out as wasmtime 49.0.2 writes
  a listing: the entries, then the count at `used`. Bytes the first listing wrote past the
  second are zeroed. If the page cannot grow, or the second listing fails or does not fit,
  the first listing and the count are zeroed and the answer is `EIO`. The guest's own forward
  still runs first, so every trap and errno of 5b's rows is unchanged. Criterion 3 gains `used`
  at `buf + 16`. The injected host bytes now follow wasmtime's layout, learnt from a listing
  with `used` outside, and are also written into the guard's private listing. Against the
  reviewed walk (plugin `oldwalk048`) it failed: `(16, {0: b'\x00\x00\x00', 25:
  b'\xa5\xa5\xa5', 51: b'\xa5\xa5\xa5'})` (`build/review-f1-f4-seen-failing.txt`). Decision 4
  and the Design line are amended.
- **F2 (the plain-name forward had no check): fixed.** I added
  `test_the_rename_is_forwarded_by_its_plain_names` (unit, `test_runner_mounts.py`). It wraps
  `_source_type` to swap `d` for `d -> ../outside` right after the stat answers "folder", and
  wraps `forward` to record what a forwarded `path_rename` names. Then `rename("d/",
  "stolen//")` must give errno 0, forwarded paths `(b"d", b"stolen")`, a grant holding only
  `stolen` (the link, `../outside`), and `outside` with its canary untouched. Every path is in
  the test's `tmp_path`. Under M1 (plugin `m1048`: `_plain` returns the path) it fails:
  `[(b'd/', b'stolen//')] == [(b'd', b'stolen')]` (`build/review-f2-seen-failing.txt`). It
  carries both your race probe and the pre-build review's lighter assertion.
- **F3 (the errno order): recorded, not matched.**
  - Decision 1's sentence, "it only ever changes an answer where a writable place lets a rename
    happen", is replaced. Decision 3 gains "The errno order, in full". Once a slash is seen, a
    bad descriptor, a read-only or mixed pair, or a path past 4,096 bytes answers the guard's
    errno (the stat's, `ENOTDIR` or `ENAMETOOLONG`) where 49.0.3 answers `EBADF`/`EPERM` first.
    It is accepted because nothing is renamed either way.
  - 5b's rule table marks four rows "order": your `read-only file, slash`, `read-only nothing,
    slash`, and two of your probe's rows added, `to a bad descriptor, slash` and `a file, slash,
    to read-only`. They are named in Decision 3 and the landing notes.
- **F4 (criterion 3's `used`-inside case could not fail): fixed.** The case moved to
  `buf + 72`. Under M4 (the reviewed walk with `keep = range(0)`) it fails: `assert 0 == 80`.
  The loop runs 72 before 16, so each case shows its own catch.
- **F5 (034 composition): extended.** "How spec 034 must compose with this" now adds four
  things. First, 034's `_write_sides` grant must become a writable `files.Guarded`; the served
  rename must require a folder source when either path ends in `/`; and the four target-slash
  rows must be re-derived out of `LINUX_ROWS`/`WASMTIME_ROWS`. Second, `table.walk()` now runs
  on every call, and a guard table is still never reported. Third, the errno order applies to
  the served rename too. Fourth, it lists the textual conflicts: `_OnStack` vs `Mounted`,
  `_instance`, `_path_rename`, `_fd_readdir`, and the README mounts bullet.
- **F6 (the citation): fixed.** The landing notes no longer cite `seen-failing-2.log` for
  criterion 2. Run alone under the fixes-off plugin, criterion 2 failed as on today's code
  (`build/seen-failing-3.log`). The table of today's answers is
  `build/seen-failing-rule-each.txt`.

Your mutant script was not re-run as it stands, because M3, M4 and M9 name text that no longer
exists. The equivalents above (the reviewed walk, M4, M1) were run as plugins, and the full judge
is below. `uv run ruff check` and `ruff format --check` are clean. The full judge after the
fixes (`build/judge-review-fix-full.log`; never `--accept`):

```
wasi_python v1: 220/231 pass · 0 gap · 11 blocked · 0 fail   (unit suite 818/826, 8 skipped)
ratchet vs c42410a127: lost 0 · absent 0 · unrun 0 · unrun locally 9 · gained 4 · grew 0 · judge changed: tests/checks/test_rules.py, tests/checks/test_v1_2_hostile_guest.py, tests/harness/files.py and 2 more
================= 1038 passed, 19 skipped in 194.00s (0:03:14) =================
```

The unit suite grows by one (the F2 check); the ratchet is unchanged: lost 0, grew 0.

## Verdict

**Not ready to land yet. Close.** The escape is closed, on every host, by the rule 49.0.3 uses,
and the checks prove it (criteria 1 and 2, EXECUTED). Calls without mounts are otherwise
unchanged in result, record and fuel. Two things must change before landing. First, the padding
walk must not trust a `d_namlen` the guest can overwrite with `used` (F1). Second, the
plain-name forward needs a check, because today one line could bring the escape back (F2). F4
goes with F1, as one more check case. F3, F5 and F6 are text: record the errno order, finish
the 034 notes, and fix one citation. No second review round is needed if the fixes are checks
and text, and the same mutants are re-run.

## One line

The rename escape is closed and proven, but a guest can aim `used` at a `d_namlen` and keep host
bytes in later entries' padding, and nothing guards the plain-name forward that closes the race,
so fix the walk, add those two checks, and record the wider errno order before landing.

## Confirmation (2026-10-18)

The same reviewer re-read the branch as fixed. That is `b559a9e` on `spec/048-the-sandbox-holds`,
the build commit rebased clean to `a37348d` on main's `b5b7869`. I read the Disposition above
against each finding, the diff `git show b559a9e`, and the new evidence files
(`build/review-f1-f4-seen-failing.txt`, `build/review-f2-seen-failing.txt`,
`build/seen-failing-3.log`). `mounts.py` is now SHA-256 `f770e8ca8048…`; `runner.py` is
unchanged. New scripts and outputs are under `…/scratchpad/048-buildreview/confirm/`. Every
grant was in a temporary folder. After every run the worktree's `git status --short` was empty
and the source hashes matched `HEAD` (EXECUTED).

**The judge (EXECUTED, `judge-confirm.log`, exit 0).** The run is `uv sync`, then
`WASI_PYTHON_ARTIFACTS=…/s-0cdc7b2bd78db6f5 uv run pytest`, with no flags. It gives `220/231
pass · 0 gap · 11 blocked · 0 fail (unit suite 818/826, 8 skipped)`, the ratchet gives `lost 0
· unrun 0 · gained 4 · grew 0`, and pytest reports `1038 passed, 19 skipped`. Both ruff runs are
clean. This equals the Disposition's numbers.

**Mutants (EXECUTED, `confirm/mutants/summary.txt`).** I adapted the script to the new code. M3
now disables the `_zeroed` call. M4 always walks the guest's bytes, which is the reviewed walk.
M9 is in `_zero_pads`. Four new mutants cover `_zeroed`. The new F2 check is in the selection.

| mutant | caught by |
|---|---|
| M1 the slash forwarded | the new `test_the_rename_is_forwarded_by_its_plain_names` (was: nothing) |
| M2, M5-M8, M10-M15 | as before, unchanged (M8 and M15 also by the new F2 check) |
| M3 no zeroing | criterion 3, 5b, criterion 6 |
| M4 the overlap ignored (the reviewed walk) | criterion 3 (was: nothing) |
| M9 a cut-short header not zeroed | criterion 3 |
| M16 the second listing not zeroed | criterion 3 |
| M17 the first listing's tail (past a shorter second listing) not zeroed | **nothing** (C1) |
| M18 the `EIO` fallback leaves the first listing in place | **nothing** (C1) |
| M19 the second listing's count not written | criterion 3 |

### Each finding

| finding | answer | confirmed? |
|---|---|---|
| F1 the walk trusted an overwritable `d_namlen` | `_zeroed` lists again on the private page when `used` overlaps the listing; criterion 3 at `buf + 16` | **yes**. EXECUTED: `used` at `+16`, `+72`, `+20`, `+76` and `−4` all give every padding zero (the `+72` row's `50` is the count itself), count 80, nothing past it touched (`confirm/probe_zeroed.txt` A, F). My original probe and M4 are caught. |
| F2 the plain-name forward unguarded | the swap-after-stat unit check, plus forwarded lengths | **yes**. M1 is caught. The check holds the escape on the outward link, and every path is in `tmp_path` (READ). |
| F3 the errno order | recorded in Decisions 1 and 3; four "order" rows in 5b | **yes** (READ). The text says what my table showed. The rows pin it. "Accepted, not matched" is a fair answer: nothing is renamed. |
| F4 the vacuous `used` case | moved to `buf + 72` | **yes**. M4 now fails it (EXECUTED; the author's log shows `assert 0 == 80`). |
| F5 034's composition | four more items in the notes | **yes** (READ). It covers the guarded `_write_sides`, the target-slash folder rule, `walk()`, the errno order and the textual conflicts. |
| F6 the citation | `seen-failing-3.log` and `seen-failing-rule-each.txt` | **yes** (READ, the files exist and show it). |

### The second-listing path, looked at closely (EXECUTED unless marked)

- **The guest's own forward still runs first.** `_zeroed` runs only after that forward answered
  0 (READ). So every trap and errno of 5b's rows is unchanged. 5b passes.
- **The page grows only on this path.** Growth happens only when `used` overlaps the listing.
  The grown page stays for the rest of the call. The stat still uses offsets 0 to 64 + path
  (READ). With `used` outside, the page stayed at 64 KiB in every probe.
- **It costs no fuel.** A metered loop of 20 listings with `used` at `buf + 16` used 345 fuel on
  both linkers. Caps 50, 200 and 333 end `OUT_OF_FUEL` with the same fuel on both
  (`confirm/probe_fuel.txt`).
- **The `EIO` fallback zeroes what it must.** I forced the private listing to fail. The answer
  was `EIO`, the count 0, the first listing all zero, and nothing past it touched (probe D). With
  a store memory limit of 64 MiB and a guest `length` of 1 GiB, the page cannot grow. The answer
  is again `EIO`, with the buffer zeroed (probe C).
- **A folder that changes between the two listings.** I removed the folder's file after the
  guest's listing and soiled that listing's padding. The guard wrote the second listing
  (`.`, `..`, count 51) with zero padding. Bytes 51 to 80 of the first listing were zeroed
  (probe E). That is a listing wasmtime could have given at that moment, and no host byte is
  left.

### Two new points (low; for the author)

- **C1. Neither branch that runs only on failure has a check** (M17 and M18 survive). The `EIO`
  fallback is not a rare path for a hostile guest. wasmtime does not check that
  `buf + length` fits. So a guest can pick a `length` above the store's memory limit (the
  default is 1 GiB per memory) and aim `used` over its listing. That reaches the fallback every
  time (probe C). If the fallback forgot to zero, the first listing's unzeroed padding would
  stay. Add two unit checks:
  - the fallback, forced as in probe D, or reached as in probe C, with injected padding: zero
    buffer, count 0, `EIO`;
  - a shrink between the listings, as in probe E, with injected padding in the first listing:
    the tail zeroed.
  Seen failing first: M18 and M17.
- **C2. The page grows to the guest's `length`, not to what its memory can hold.** With no store
  limit, `length = 0xFFFFFFF0` grew the private page to 4,096 MiB. That is virtual memory; the
  process's max RSS stayed at 43 MiB. With the default 1 GiB limit, any `length` above it gives
  `EIO`, where wasmtime 49.0.2 answers 0. Use `min(length, memory.size - buf)` for the second
  listing. It is free: the first listing already fit in `[buf, memory.size)`, and the second
  must fit there anyway (`memory.fits(buf, again)`). It keeps the page no larger than the guest's
  own memory, and it removes the `EIO` a guest can choose (INFERRED from the code; probe B and C
  are the evidence for today's behaviour). Fix it, or answer in writing. A guest that aims `used`
  into its own buffer is not a real program, so the changed answer harms no one.

### Verdict on the revision

**Confirmed: 048 lands once C1's two checks are in.** C2 must be fixed or answered in writing.
All six findings are fixed or recorded as asked. The escape and its race are closed and guarded.
The padding is zero wherever the guest puts `used`. Calls without mounts are unchanged in record
and fuel. C1 adds checks only, and C2 at most one line. So no further review round is needed.
The lane confirms that M17 and M18 now fail (the script is
`confirm/mutants/run_mutants.py <out-dir> "M17 first listing's tail not zeroed" "M18 EIO
fallback leaves the first listing"`; or the author's equivalent plugins) and that the judge stays
at lost 0 and grew 0.

One line: F1 to F6 are fixed or recorded, and the second listing zeroes correctly on every path I
drove, so 048 lands after two checks for its fallback and shrink branches, with the page capped
at the guest's memory or the reason written down.

### Author's note (2026-10-18)

C1 and C2 are met in `3ce5c83`: two checks hold the fallback (fails under M18, `assert 80 == 0`) and the shrink (fails under M17, the old `x.txt` entry and `a5a5a5` left past byte 51), the second listing asks for `min(length, memory − max(buf, 8))` with a check that failed first (page 4 GiB against the guest's 128 KiB), and the full judge is 220/231, 0 fail, lost 0, grew 0, unit suite 821/829.
