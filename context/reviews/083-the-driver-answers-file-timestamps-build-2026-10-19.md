# Build review of 083 — the judge's driver answers a file's times and inode number itself, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 083's code, its specification or its pre-build
  review.
- **Under review:** `spec/083-the-driver-answers-file-timestamps` at `e8b914b`, on main
  `9d89535`. Main is now `3866f56`; the commits after `9d89535` touch only `context/` and
  `README.md`.
  - The code commits: `0bc21ea` (the checks first), `29e6794` (the driver), `cb67e4b` (the
    file-facts check reads the guest's clock), `e511da2` (Decision 8), `c682177` (the probes take a
    private set), `51f3402` (CHANGELOG, Kind line). `e8b914b` is the landing notes.
  - The builder's evidence: `context/research/2026-10-19-what-the-guest-learns-about-a-file/at-build/`.
- **How I ran it:**
  - The judge in the 083 worktree, against my own clone of the frozen set
    (`cp -c -Rp build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, every file checked with
    `shasum -c SHA256SUMS`).
  - The worktree's `build/progress/latest.json` was copied aside first and put back after; it is
    byte-for-byte the file I found.
  - Every probe ran in my scratch folder, in three `git clone --shared` copies of the branch:
    - one at a checkout path about 130 characters longer (`a-considerably-longer-…/x/`);
    - `variant/w`, patched to choose the inode answer (`P083_INO`);
    - `variant2/w`, patched to round host times to a coarse tick (`P083_COARSE`).

    Each has an APFS clone of the worktree's source trees and tarballs. I wrote nothing in any
    git tree.
  - The scratch folder is
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/083-buildreview/`
    (`probes/` holds the scripts and outputs).

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

- It is built as the specification says. The five shadows, the two trampolines, `FileFacts`, the
  fuel loan, the per-run stdlib copy (clone on darwin) and the release after `store.close()` are
  all there.
- **Fuel is exact.** My full judge (`-n 3`, on `e8b914b`) gives every one of the 168 fuel rows
  the builder's value to the instruction. `sameness.py` finds no difference.
- **Cross-host: nothing host-dependent that I could find still reaches fuel on a darwin APFS
  host.** `cpython-fs` gives **59,778,645,587** in the builder's runs, in my full judge, and in a
  serial run from a checkout path 130 characters longer, with another `TMPDIR` and another set
  path (EXECUTED).
  - One assumption is left: the host gives every change to a file its own time stamp. The
    runner's macOS VM was not measured. Simulated, a 1 µs host tick moves nothing, and even a
    1 ms tick moves `cpython-fs` by only 0.11 parts in 10^4, a tenth of the tolerance (section 2).
- **The growth's cause is confirmed** on four rows, by measurement: it is the inode number's
  size. A count from 2**62 (three 30-bit digits, as wasmtime's hashes mostly were) puts each row
  back on its accepted value.
  - That measurement also shows that Decision 3's reason for a count from 1 no longer holds on
    this base (F1).
- **Security:** the shadows behave exactly as main's driver on every hostile edge I tried
  (EXECUTED). Fuel cannot be stolen. The guest learns less about the host than before.

Four findings, none in the code's correctness: F1 medium (a stale reason), F2 to F4 low.
**It lands once F1 is answered in writing** (section "Verdict").

## 1. The diff against the specification (READ)

- **Decision 1, the shadows.**
  - `FILE_CALLS` names the five calls with their wasm signatures.
  - `forwarders_wat` builds a module that imports wasmtime's own calls and the guest's memory,
    and exports one forwarding function for each call.
  - `_FileCalls.bind` makes a plain `define_wasi()` linker on the same store, so the descriptor
    table is the same. It instantiates the trampoline on the guest's memory, and the second one,
    for the two stats the driver makes for itself, on a page of its own.
  - `run()` binds right after `linker.instantiate`, before `set_fuel(fuel)`.
  - Only a successful answer is rewritten: a stat's `ino` (8 bytes at 8) and its three times (24
    at 40), and a listing's `d_ino` and padding.
- **The fuel loan.** `call` reads the fuel, sets it to `min(before + 2**20, UNMETERED)`, forwards,
  and sets `before` back in a `finally`. It does nothing when the run counts no fuel (`own=`).
- **Decision 2, the times.**
  - `FileFacts.stamp` keeps each file's host times and its answers, keyed by wasmtime's hash.
  - A new or moved `mtim`/`ctim` takes one clock value for all its new fields. `atim` moves only
    with them (`fresh[0] = old is None or fresh[1] or fresh[2]`).
  - A set-times call is re-statted on the driver's own page. `set_times` records the chosen
    exact or "now" values against the host's values.
- **Decision 3, the inode.**
  - `ino()` gives `setdefault(real, len + 1)`; 0 stays 0.
  - `listing()` renumbers each whole entry and zeroes its padding. Of a cut entry it zeroes only
    the `d_ino` and padding bytes present.
  - A count lying over its own buffer is left alone, as written.
- **Decision 4.** `dev`, `nlink`, `size` and the file type pass through. `Turns` is not shadowed.
  `own=` runs are shadowed with no fuel work.
- **Decision 5.** The real-metadata check's docstring gains its sentence. The builder's two
  mutants (inode 0, time 1767225600 s) fail it on both binaries (`mutants.out`).
- **Decision 8.**
  - `stepped-clock.txt` drops the two `test_utime_current` ids.
  - The class's `match` keeps only `No rotated files found`.
  - The gap names 1 finding, digest `896f645c570d`.
  - My judge agrees: the class check is a gap with that digest, and `cpython-fs` has 3,712 passes.
- **Decision 10.**
  - `_place` clones on darwin (`clonefile`), and falls back to `copyfile`; a folder still goes
    through `copytree`.
  - `_release` closes the store, then removes `lib` with errors ignored. It runs after a normal
    end, and on any exception out of the guest's calls. `Turns.close` does the same.
- **The checks.**
  - `test_file_facts_cost_the_same_on_every_run` and `test_fuel_does_not_follow_the_stdlib_zips_link_count`
    are as specified. Their host-independent assertions run everywhere; fuel and output are
    compared on darwin only.
  - The link counts are 1,101, or 1,021 on Windows (A2).
- **The unit rows.** The five rows are as specified, and the cut-entry row walks every cut byte.
- **The departures** (the landing notes list four, not five; F3):
  1. The check reads `clock_gettime_ns(CLOCK_REALTIME)`, not `time.time()`, because the
     rule's text scan cannot tell a guest's clock from the host's. **Accepted**: it is the same
     clock in the guest.
  2. `bind` makes its own plain linker, and has no separate assertion. **Accepted**: `bind`
     either sets every forwarder or raises, and a forwarder that is `None` raises the named
     `RuntimeError`.
  3. An exception before the guest's calls leaves the run's copy behind. **Accepted**: the
     `guest_workdir` fixture removes its folder at teardown, and no other run reads it.
  4. The CHANGELOG entry. **Accepted**: the text is accurate.
  - Not declared: the driver now needs a guest that exports `memory` (F3).
- **Criteria 0 to 9** are each evidenced in `at-build/`. One exception: criterion 1's "against
  the draft's prototype" half is shown only by the pre-build review's `revised/` runs, not again
  at build (F3, a nit).
- `ruff check` and `ruff format --check` pass on `src/` and `tests/` (EXECUTED).
- The tree has no `os.link` of a guest-visible host file left (READ, grep). The guest programs'
  own `os.link` rows run inside the guest.

## 2. Cross-host determinism: the crucial question

### What I measured (EXECUTED)

| run | checkout | TMPDIR | set path | workers | `cpython-fs` fuel |
|---|---|---|---|---|---|
| builder, five passes and the full judge | `…/wasi_python-083` | default | `build/set-083` | 3 | 59,778,645,587 |
| my full judge, on `e8b914b` | `…/wasi_python-083` | default | scratch `set/` | 3 | 59,778,645,587 |
| my long-path run | `…/083-buildreview/a-considerably-longer-checkout-path-to-move-every-host-path-length/x/wasi_python-083` | `…/another-temporary-folder-with-a-much-longer-name-than-var-folders` | `…/set-copy-two` | serial | 59,778,645,587 |

- The checkout path, the temp folder, the set's path, their lengths, and the scheduler do not
  reach `cpython-fs`'s fuel. Before 081 and 083, each of them could.
- All 168 fuel rows are identical, to the instruction, between the builder's record
  (`build/083/latest-full.json`, on `51f3402`) and mine. `uv run python tests/harness/sameness.py`
  on the two prints nothing and exits 0.
- After both full judges, the set zips each have one link, and nothing under the worktree or
  my scratch folder shares their inode (`find -samefile`). No run's stdlib copy is left
  behind in `build/harness/`.

### What the guest can still learn from the host (READ, with probes where marked)

I went through the calls the judge's guests make, and what each answers after 083.

- **A stat** (`fd_filestat_get`, `path_filestat_get`):
  - `dev` is always 1 (wasmtime's `p1.rs`).
  - `ino` and the three times are answered by the driver.
  - The file type is the host's.
  - `nlink` and `size` are the host's:
    - A file's `nlink` is 1 now: nothing the guest sees is linked from outside its run.
    - A file's `size` is bytes the check or the artifact chose.
    - A folder's `size` and `nlink` on APFS depend only on the set of names in it. They do not
      depend on the creation order or on entries deleted earlier (EXECUTED: three folders of
      the same 40 names, one made in reverse, one after 100 deletions, all give `size 1344
      nlink 42`).
- **A listing** (`fd_readdir`):
  - The names are the check's or the guest's.
  - The order is the file system's. On APFS (case-insensitive) it depends only on the names: the
    three folders above list in one order, and not sorted. So the order of first sight, which
    sets the inode counts, is fixed.
  - The cookies are indices. `d_ino` is answered and the padding zeroed.
  - wasmtime computes each `d_ino` by `metadata_hash_at`, the same hash as the stat, on Unix and
    on Windows (READ, `wasmtime-wasi-49.0.0/src/p1.rs`, `filesystem/windows.rs`). So the
    check's `DirEntry.inode() == st_ino` holds on Windows too.
- **The environment and argv:** only what the check passes. For CPython's groups that is
  `TMPDIR=/tmp HOME=/tmp`. 081 refuses any host path under the checkout or the temp folder.
- **The grants:** guest paths only. CPython's stage holds the tarball's `Lib/test` members,
  written by the judge, and nothing a build left there.
- **No WASI call exists** for uid, gid, hostname, free space, CPU count or the time zone. So
  the guest gets wasi-libc's constants (INFERRED from the preview1 call list; I did not read
  wasi-libc).
- **The clock, its resolution and random** are answered (002, 065).
- **Unanswered, but fixed:** `poll_oneoff`. A relative timeout sleeps on the host and then fires.
  An absolute one, taken from the driver's 2026-01-01 clock, is in the past for the host and
  fires at once. Stdin is empty and files are always ready, so no readiness race decides an
  event (INFERRED).
- **Host paths in error text:** wasmtime maps host errors to errno values, and returns no text.

### What is left

1. **The time-stamp assumption.** The driver treats a host time as moved when it differs from
   the last one seen. If two changes to one file landed in one host clock tick, the second would
   go unseen: one less clock step, so every later time in that run shifts by 1 µs.
   - On this machine APFS stamped each of 5,000 writes apart (the spec's `granularity.out`;
     smallest step 2.9 µs). Apple-silicon kernels stamp from the 24 MHz timer, VMs too, so the
     runner should behave the same (INFERRED; the runner was not measured).
   - **The size, simulated (EXECUTED):** I rounded every host time down to a coarse tick before
     the driver compared it, and ran `cpython-fs` (`probes/coarse-*.json`):

     | host tick | `cpython-fs` fuel | against the build | outcomes |
     |---|---|---|---|
     | none (the build) | 59,778,645,587 | — | 3,712 passes |
     | 1 µs | 59,778,645,587 | 0 | the same |
     | 1 ms (coarser than any APFS host) | 59,779,282,175 | +636,588, **0.11 parts in 10^4** | the same (3,712 passes; 6 failed, 59 errors as before) |

     Even a host stamping by the millisecond stays at a tenth of the tolerance on this group, and
     at 1 µs nothing moves at all. The rounding is a simulation (it rounds at compare time, not at
     write time), so this sizes the effect; it does not reproduce a host.

   - The new check `test_file_facts_cost_the_same_on_every_run` asserts same output and same
     fuel on darwin, so the release's macOS `verify` job would show a host that stamps coarsely.
2. **The volume format.** A case-sensitive APFS volume orders listings in another way. GitHub's
   macOS images use case-insensitive APFS, like this machine. It is noted, not measured.
3. **The macOS version.** The lane runs Darwin 25 and `macos-15` runs Darwin 24. I know of no
   difference in what wasmtime answers between them, and I cannot measure one here.
4. **Linux and Windows,** which are not ratcheted, keep host-dependent fuel. Decision 6 says so.
   - On Linux, ext4 orders listings by a hash seeded per file system, so the order of first sight
     differs between machines. It also reuses freed inode numbers, and stamps ctime coarsely.
   - On Windows, NTFS lists in name order and rounds times to 100 ns. A set time comes back
     exactly as the guest set it, because the driver keys it to the host's rounded value
     (READ, `set_times`).
   - None of this reaches a ratcheted record.

**The answer.** After 083, the three causes 065's review named (file times, inode numbers, the
zip's link count) are gone, and I found no fourth one. The one input left is whether the runner's
file system stamps every change apart. Simulated, it is worth at most about 0.1 parts in 10^4 on
`cpython-fs`, and nothing at a 1 µs tick. So I expect the next macOS dry run to match the lane.

## 3. The growth: is the stated cause right? (EXECUTED)

On a patched clone (`probes/variants.sh`), I chose the inode answer through an environment
variable and ran rows of the growth list:

| row | accepted | the build (count from 1) | wasmtime's hash (times only) | count from 2**31 (two digits) | count from 2**62 (three digits) |
|---|---|---|---|---|---|
| `test_kiwisolver_raises_unsatisfiable_constraint[snapshot]` | 20,996,483 | 21,011,669 | 20,996,483 | 20,996,466 | **20,996,483** |
| `test_files_by_path_in_grants[snapshot]` | 219,244,114 | 219,275,491 | 219,244,080 | 219,243,927 | **219,244,114** |
| `test_files_by_path_in_grants[plain]` | 493,206,148 | 493,266,086 | 493,206,148 | 493,205,910 | **493,206,148** |
| `test_upstream_suite[pandas-reshape]` | 102,664,111,646 | 102,767,163,170 | 102,664,115,398 (builder's) | — | **102,664,119,053** |

- **The builder's cause is right.** The times barely move these rows. The whole rise comes from
  the inode number's size: put back three digits and each row returns to its accepted value,
  exactly on three rows, and within 7,407 of 102.7 billion (0.0007 parts in 10^4) on
  pandas-reshape.
  - The 2**62 runs' ratchet line reads `grew 0`. The count-from-1 run reads `grew 3`.
- **Why one digit costs more, not less, is still unexplained.** Two digits cost 17 to 238 fewer
  instructions than three; one digit costs 15,186 more on kiwisolver and 103 million more on
  pandas-reshape. The notes' "an int's digits, hashing, the allocations after" is a label, not a
  mechanism. It stays INFERRED, as the notes say. It does not make the restated values wrong:
  each is one value over six runs.

## 4. Security (EXECUTED, `probes/hostile.py`, `hostile.out`)

I ran nine hostile calls through main's driver and through 083's, and compared exit, trap, fuel
and door frames:

| case | main | 083 |
|---|---|---|
| stat whose answer runs past memory's end | trap, fuel 4 | the same |
| stat into the last 64 bytes | exit 0, fuel 23 | the same; the frame carries count 1 and clock times |
| `path_filestat_get` to address −8 | trap, fuel 7 | the same |
| listing whose `used` pointer lies in its own buffer | exit 0; wasmtime's hashes | the same: left alone, as Decision 3 says |
| listing into a 1-byte buffer, and a 30-byte buffer | exit 0 | the same; the cut header's `d_ino` zeroed, the whole entry renumbered |
| listing whose buffer runs past memory's end | trap, fuel 7 | the same |
| set-times by a 60,000-byte path (`./` × 29,999, then `f`) | exit 0, fuel 480,030 | the same; the own page grew, and the times come back as set (5, 6) |
| set-times with both "exact" and "now" | errno 28 | the same; nothing recorded |

- **Out-of-bounds writes:** the driver writes only where wasmtime has just written the same
  number of bytes, successfully. A failed or trapping forward rewrites nothing. The guest is
  single-threaded with no shared memory, so nothing changes between the forward and the rewrite.
- **Fuel theft:** no guest instruction runs on lent fuel. The trampoline imports no guest
  function, and wasmtime's WASI code never calls back into wasm. `before` is restored in a
  `finally`, also after a trap. The cost row and the edge row hold (my mutant without the loan
  fails the cost row: `probes/mutants.out`).
- **TOCTOU:** the only window is between a set-times call and the driver's own re-stat. Only a
  host process could act in it, and the worst it could do is a wrong answer in the judge. The
  product runner has no shadows.
- **What the guest learns:** less than before. Counts replace hashes, and clock values replace
  host times. The re-stat's page is not the guest's. The one case left as wasmtime wrote it (a
  count lying over its own buffer) is the same as on main.
- **Host resources:** the own page grows to the longest path a set-times call used, and
  never shrinks. The copy is unmetered host work, bounded by the guest's 4 GiB. This driver runs
  only the project's own artifacts, so I make no finding of it.

## 5. The full judge (EXECUTED)

`WASI_PYTHON_ARTIFACTS=<scratch>/set uv run pytest -n 3` in the 083 worktree, on `e8b914b`
(clean, `dirty: false`), while other judges ran on the machine (load about 28 on 10 cores):

- `wasi_python v1: 527/627 pass · 77 gap · 23 blocked · 0 fail (unit suite 1584/1592, 8 skipped)`.
- `2111 passed, 31 skipped, 77 xfailed in 511.07s`.
- `ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 4 · grew 22 ·
  more 1 · judge changed`.
- The 22 grown rows, and each row's value, are exactly the landing notes' table (recomputed from
  my record against `accepted.json`).
- **My record:** `<scratch>/reviewer-latest.json`. The log is `<scratch>/full-judge.log`.
- **Sameness** with the builder's `build/083/latest-full.json`: no difference, and the fuel is
  equal on all 168 rows, not just within tolerance.

## Findings, most severe first

### F1 (medium): Decision 3's reason for a count from 1 is stale on this base

- **What the spec says:** Decision 3 says a count from 2**63 "would leave out the inode's part of
  the moves … but the times' part alone still moves 21 to 24 rows past the tolerance. So an
  acceptance is needed either way, and the plain count is the simpler answer." Decision 7 says
  the same.
- **What the build's own evidence shows:** on `9d89535`, the times-only column is +0.00 to
  +0.01 parts in 10^4 on all 22 grown rows. Across all 164 rows, the times alone move only
  `cpython-fs` past one part in 10^4, and that is a fall (−6.15) (`growth.out`).
- **What I measured:** a count from 2**62 returns four of the 22 rows to their accepted values,
  to the instruction or within 0.0007 parts in 10^4 (section 3). So on this base, a three-digit
  count would probably need **no** `--accept-growth` at all. That is untested on the other 18
  rows.
- **Why it matters:** the lane accepts growth on the strength of the stated reason. Right now
  the reason for the choice that causes the growth is false, and accepting growth when it could
  be avoided is not what rule 5 means by a stated reason.
- **Fix, either one:**
  - (a) In writing: correct Decision 3 and the growth reason, keeping the count from 1. Say that
    on this base a three-digit count would avoid the growth (measured here on four rows), and
    give the reason the count from 1 is still preferred (for example, it is simpler to read and
    assert, and a high base fixes no host input). That is a `context/` change only.
  - (b) In code: answer `2**62 + count`. Change the `< 2**30` assertions in the unit row and in
    the new check, measure all 168 rows again, and drop the growth list for whatever returns.
- I would accept (a), given that every dry run is red until 083 lands. (b) can follow as its own
  change.

### F2 (low): the worktree's `build/progress/latest.json` is not the full judge's record

- The notes say the record is `build/progress/latest.json`, with a copy at
  `build/083/latest-full.json`.
- The first file is now a later partial run: 44 checks, `dirty: true`, no artifact, at 17:41Z.
  Only `build/083/latest-full.json` (627 checks, on `51f3402`, 17:39Z) is the full judge.
- **Fix:** the lane's sameness step must use `build/083/latest-full.json`. Correct the notes'
  sentence.

### F3 (low): departures and evidence, as written

- The notes list four departures; the builder's report counts five.
- **Not declared:** `bind` reads `guest.exports(store)["memory"]`, so a guest that exports no
  memory now makes `run()` raise `KeyError: 'memory'`. Main's driver ran such a guest to its exit
  (EXECUTED, `probes/nomemory.out`). No guest of the judge lacks the export, and the suite is
  green, but it is a change in the driver's contract.
  - **Fix:** declare it as a departure, or bind only when the guest exports memory (an unbound
    shadow then raises the named `RuntimeError` on first use).
- **Criterion 1's prototype half** (the read, cut-entry, zero and edge rows failing against the
  draft's prototype) is evidenced only by the pre-build review's `revised/` runs. Say so in the
  notes.

### F4 (low): the unit rows do not guard "no clock step" for stdio's zeros

- Decision 3 (the pre-build review's F4) says a zero passes through "with no stamp and no clock
  step".
- **The gap:** a mutant without the explicit shortcut (`if real_ino == 0 and not any(real)`)
  passes all five unit rows (EXECUTED, `probes/mutants.out`). The per-field `0 if real[i] == 0`
  still answers zeros, so only the clock step differs. fd 1 is the last stat in `FILE_FACTS`, so
  no later answer shows it.
- The ratchet would still catch such a regression on any CPython guest, which stats its stdio at
  start. So the judge as a whole has no hole here; the unit row claims more than it checks.
- **Fix:** one more stat of `f` after fd 1 in `FILE_FACTS`, or a `FileFacts` row asserting that a
  zero answer leaves the clock where it was.

## Notes (no action)

- **N1.** `atim` follows `ctim` as well as `mtim`. A utime that sets only `mtim` (UTIME_OMIT for
  atime), a hard link or a rename moves the host's ctime, so it gives `atim` a new value. A
  `noatime` host would not do that. Python's `os.utime` always sets both, and the answer is
  deterministic. The spec documents the write case; this is the same rule.
- **N2.** A time of exactly 0 on a host file with a non-zero inode is answered 0 (per field), as
  the guest would see on the host. It is deterministic.
- **N3.** For the lane: the landing notes' `--accept-judge` and `--accept-growth` texts are
  accurate as to what grew and why. If F1 is answered by (a), the growth text should add that a
  three-digit count would avoid it.

## Verdict

The code is correct, and the fuel is exact: across workers, checkout paths, temp folders and set
copies, every row gives one value. The growth is real, and its stated cause is confirmed. The
one thing I cannot close here is the runner's time-stamp granularity. Section 2 sizes it at
under a tenth of the tolerance even for a 1 ms host.

**Lands once F1 is answered in writing** (option (a) is enough). F2 to F4 are low: fix them in the
same `context/` commit or answer them there; none needs a code change before landing.

One line: 083 makes fuel independent of host times, inode numbers, link counts, paths and temp
folders, which I confirmed to the instruction; it lands once its stale reason for a count from 1
(F1) is corrected.
