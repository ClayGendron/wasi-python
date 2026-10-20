# Build review of 089 — host litter never reaches a verdict: the judge seals its stages and watches its grants, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 089's code, its specification, its memo or its
  pre-build review.
- **Under review:** `spec/089-host-litter-never-reaches-a-verdict` at `6f525a0`, on main
  `3866f56`.
  - `e115d00` and `0ae5253`: specs 089 and 090, the memo, the roadmap lines (`context/` only).
  - `d4a46d5`: the build, `tests/` only: `tests/harness/litter.py` (new),
    `tests/unit/test_host_litter.py` (new, 18 rows), the check
    `test_a_file_dropped_into_a_stage_changes_nothing` appended to `test_v1_4_embedding.py`, and
    edits to `guest.py`, `regrtest.py`, `upstream.py` and both conftests.
  - `6f525a0`: the revised specification (Disposition of F1 to F9, "For the lane", landing notes)
    and the evidence under `context/research/2026-10-19-ds-store-in-the-judges-stages/at-build/`.
- **How I ran it:**
  - The full judge in the 089 worktree, at `6f525a0`, clean, against my own clone of the frozen
    set (`cp -c -Rp build/sets/s-c50ca51fae5eb55b-c9dcb5b8`, `shasum -c SHA256SUMS` OK, no file
    with nlink above 1), through `WASI_PYTHON_ARTIFACTS`. `-n 3`, because spec 078's judge was
    running on the machine. Log and record in the worktree's `build/089-review/`.
  - The worktree's `build/progress/latest.json` is now my record (as the lane asked). The
    builder's full record is untouched at `build/089/latest-full.json`.
  - Every probe, kill and mutant ran in my scratch folder, never in the worktree:
    `git archive` copies of `6f525a0` (`tree/`, `t089/`) and of `3866f56` (`main/`), the latter
    two with APFS clones of the worktree's CPython tarball and tree; probes used a second private
    set (`set2/`) so they could not touch the full judge's set.
  - The scratch folder is
    `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/089-buildreview/`
    (`probes/` holds the scripts and outputs). I wrote nothing in any git tree and nothing in the
    main tree's `build/`.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

- **It is built as the specification says,** and the pre-build review's F1 to F9 are each fixed
  or answered (section 2). The judge seals the CPython stage, the upstream stage, matplotlib's
  data and each run's stdlib folder; it watches every `guest.run` grant before and after; the
  three stage writers refuse a litter-named member; removal unseals first and retries.
- **Fail-closed holds** for every grant `guest.run` makes, on darwin, Linux, as root and on
  Windows (section 3). The seal refuses; whatever gets past it is named by `HostLitter`. I found
  no path by which `guest.run` returns a result with litter in a grant.
- **The judge (EXECUTED):** 525/625 pass · 77 gap · 23 blocked · 0 fail, the builder's counts.
  `sameness.py` between the builder's record and mine: **no difference**. The judge hashes are
  the same (`8a4668cd…`), so the builder's record was taken on exactly the committed code.
- **But my record is red:** `GREW … [cpython-c]: fuel 372,458,058,296 -> 372,503,229,930`
  (+1.21e-4, just past the 1e-4 tolerance). Against main `3866f56` on the same set (section 5,
  three alternating runs each), main and 089 spread over the same band, up to +8.5e-5 and +9.3e-5.
  So the row is this base's own noise on the CPython groups as far as I can measure, not 089's.
  "For the lane" promises "grew 0" and has no instruction for this case (F3).
- **A killed judge now leaves every run's stdlib folder sealed,** not only its stages, and then
  `rm -rf build` and `git worktree remove` both fail (EXECUTED; F1).
- **083's rebase is one textual conflict, but not only textual:** 083's `_release` removes `lib`
  with `shutil.rmtree(…, ignore_errors=True)`, which silently removes nothing from a sealed
  folder (EXECUTED; F2).

Three findings to fix before landing (F1 to F3), four notes. **It lands once F1 to F3** (section
"Verdict"). None is in the seal or the watch themselves.

## 1. The diff against the specification (READ)

- **Decision 1, the names.** `LITTER_NAMES` is `paths.OS_LITTER` plus `ehthumbs.db`, `Icon\r` and
  the six volume-root names; `is_litter` adds the `._` prefix. `paths.OS_LITTER` is unchanged.
- **Decision 2, the seal.** `seal` clears the write bits of every folder `os.walk` yields (never
  a file, never a link followed), then removes litter in up to `SEAL_ROUNDS` = 10 rounds, opening
  each file's folder for its unlink alone and closing it in a `finally`, else `HostLitter`. On
  Windows `_set_writable` returns at once, so only the cleanup runs. Sealed: `regrtest.Session`
  after `judge/`; `upstream.Session.prepare` after every package is staged; `mpl_data_dir` after
  `extractall`; `guest.run`'s `lib` after `_place`.
  - The writers: `regrtest.stage` (each tarball member's `rel`), `upstream.stage` (each `rel`),
    `upstream.safe_unzip` (each wheel member, before anything is written) call `litter.refuse`,
    which looks at every path part.
- **Decision 3, removal.** `remove` unseals (top-down, carrying on past a folder it cannot change),
  `rmtree(ignore_errors=True)`, up to `REMOVE_TRIES` = 5; a leftover is unsealed and named on
  stderr with the recovery. Both `Session.close`, both `Session._run`, `guest_workdir` and `work`
  use it. No sweep, with the reason written.
- **Decision 4, the watch.** `guest.run` builds `Watch(ordered)` from the exact list it preopens,
  after `lib`, `mpl-data` and the extras are in it, and before any `preopen_dir`; `watch.after()`
  runs after fuel is read and before the `Result` is built. A read-only grant is compared by its
  whole inventory; any grant is scanned for litter names. `HostLitter` is an `AssertionError`;
  nothing between `guest.run` and a check catches it (my grep of `regrtest.py`, `upstream.py`,
  both conftests).
- **Decision 5, the check.** As written, with the `binds` branch (F1 of the pre-build review).
- **Scope.** No `src/`, `scripts/`, `recipes/`, `downloads/` or workflow change (READ,
  `git diff --stat`). No existing check, golden, gap or allowance edited: the only change to an
  existing check file is the appended check, and `tests/upstream/`, `tests/known_gaps.toml` and
  `context/progress/` are untouched (READ). `ruff check` and `ruff format --check`: green
  (EXECUTED).

## 2. The pre-build review's findings

- **F1 (Windows): fixed.** `binds = sys.platform != "win32" and os.geteuid() != 0` short-circuits
  before `os.geteuid`, which Windows lacks; the same in the unit file's `BINDS`. I simulated
  Windows on darwin (EXECUTED, `probes/simwin.out`): `_set_writable` a no-op and `binds` false,
  the drop check passes on both binaries (the drops land, `HostLitter` names
  `/stage/.DS_Store (before the run)`, the twin is measured last) and the unit file gives 19
  passed, 1 skipped. Guest paths in the message are built from `as_posix()`, so they read the
  same on Windows.
- **F2 (power): fixed.** I re-ran mutant (a), `seal` a no-op (EXECUTED, `probes/noseal.out`):
  both rows fail with `HostLitter: … /stage/.DS_Store (before the run); /stage/judge/.DS_Store …`.
  The builder's mutant (b) lines are in `at-build/mutants.txt`.
- **F3 (killed runs): fixed as asked, but the build widened what a kill leaves** (F1 below).
- **F4 (stdlib folder, writable roots): fixed.** Both `_run`s remove through `litter.remove`;
  Decision 2 says writable roots are detection-only.
- **F5 (for the lane): fixed,** with one case missing (F3 below).
- **F6 (a real input deleted): fixed for the three writers named;** two smaller writers have no
  guard (N1).
- **F7 (083's rebase): answered for the order;** the removal is missing (F2 below).
- **F8 (main's noise): answered;** it happened in my run (section 5, F3).
- **F9 (small points): fixed.** The refusal row skips on Windows and as root; every sealing row
  uses `tmp_path` or `litter.remove`; `ehthumbs.db` is listed; Decision 2 says the cleanup still
  runs on Windows; the Intent says "silently".

## 3. Fail-closed (READ, with probes where marked)

- **darwin and Linux, not root.** Every read-only folder `guest.run` grants from a stage is
  sealed before the `Watch` is built; a user process cannot add an entry (the unit row, EXECUTED).
  If one appears anyway, the watch names it before or after the run.
- **As root, and on Windows.** Modes do not bind; the watch alone holds: any litter name in any
  grant before or after, any entry change in a read-only grant. Simulated Windows: EXECUTED above.
- **Read-only grants that are not sealed.** A check's own read-only preopens (lxml's `ro-*`,
  `test_extra_preopens_work_on_the_snapshot`'s `data-*`) are watched, not sealed: a drop fails
  the run, loudly. Decision 2 calls only writable roots "detection-only"; these are too (N2).
- **Writable roots** are detection-only, as stated: litter names only.
- **What is not watched at all:** `Turns` instances and the product runner's own runs
  (`runner-*` folders under `guest_workdir`). The spec puts both out of scope (Decision 4,
  Scope), but the Intent's "whichever process writes it … any grant that changes anyway fails its
  run" reads wider (N2).
- **What the watch cannot see:** a litter file written and removed again within one run (Finder
  does not remove `.DS_Store`), and a non-litter file a host process drops into a stage *while it
  is being staged*, before the seal (it is then in both inventories). Neither has been seen; I
  record them as limits, not findings.
- **Nothing is filtered or retried.** The seal's cleanup touches only files that landed before
  any guest ran, and no caller retries a `HostLitter`.

## 4. Cleanup (EXECUTED, `probes/int-n2.out`, `kill-n2.out`, `release_on_sealed.out`)

- **After my full judge:** no folder under the worktree's `build/harness` lacks its owner's write
  bit; no `run-*` stage is left (criterion 5 holds).
- **Ctrl-C** (SIGINT to the whole process group, 75 s into a two-worker run of
  `test_v1_4_embedding.py` and `test_v1_3_matplotlib.py`): exit 130; every session fixture's
  teardown ran; nothing sealed, nothing left under `build/harness`.
- **SIGKILL** at the same point: exit 137; **27 folders left without the write bit, all
  `guest-*/run-N/lib`** (15 and 12 in the two workers' folders). `rm -rf build` then fails:
  `rm: build/harness/guest-…/run-11/lib/python315.zip: Permission denied`. In a throwaway repo,
  `git worktree remove --force` on a worktree holding one 0555 folder fails with
  `error: failed to delete …: Permission denied` (exit 255). `chmod -R u+w build` and then
  `rm -rf` take everything. SIGTERM ends a Python process without teardown too (no handler is
  installed), so a timeout or a task stop leaves the same (INFERRED).
- **Concurrent workers.** Every stage, run folder and mpl-data folder is a fresh `mkdtemp` of one
  process; `seal` and `remove` touch only their own roots (READ). The `-n 2` kills above left only
  the two workers' own folders.
- **Stale stages:** no sweep, argued in Decision 3. The argument holds for a pid marker. A sweep
  keyed on an advisory lock (`fcntl.flock` on a file in each `guest-*` and `run-*` folder,
  released by the kernel when its holder dies, so no pid reuse) would not have that weakness; I
  offer it in F1, not as a requirement.

## 5. Determinism, and the red row (EXECUTED)

- **089 adds nothing that depends on worker count** (READ): no shared folder, no global count,
  no ordering across processes; the watch's walks read only.
- **The full judge.** Against `accepted.json`, 164 fuel rows compare. Largest moves, builder then
  me:

  | row | builder | reviewer |
  |---|---|---|
  | `cpython-c` | +4.08e-05 | **+1.21e-04** |
  | `cpython-fs` | −5.34e-05 | +1.09e-05 |
  | `cpython-a` | −3.71e-05 | +3.58e-05 |
  | `cpython-archives` | +3.37e-05 | +1.51e-05 |
  | next (`pandas-tslibs`) | +9.05e-07 | +7.43e-07 |

  Only the CPython groups move by more than 1e-6, and they move both ways: the noise 083 removes
  (real inode numbers and times reach the guest on this base).
- **Main against 089, `cpython-c` alone, alternating, the same private set** (`probes/cpyc.sh`,
  `cpyc.out`):

  | run | main `3866f56` | 089 `6f525a0` |
  |---|---|---|
  | 1 | 372,489,849,410 (+8.54e-05) | 372,492,795,581 (+9.33e-05) |
  | 2 | 372,473,246,788 (+4.08e-05) | 372,486,396,062 (+7.61e-05) |
  | 3 | 372,458,082,288 (+6.4e-08) | 372,458,047,886 (−2.8e-08) |

  (against the accepted 372,458,058,296; the set's zip at 1 link after each run; nothing left
  sealed.) Main and 089 spread over the same band, 0 to about 9e-5, in alternating runs. So 089
  adds no visible shift. My full judge's +1.21e-4 is past what these six runs showed, so I cannot
  prove it is the same noise from six samples. But main alone moves this row by 8.5e-5 in three
  runs, which is most of the tolerance, so a crossing on main is plainly possible. That is the
  hazard F3 is about.

- **A possible contamination, probably not the cause.** My two kill tests ran in the first minutes of my full
  judge and, before I switched them to `set2`, against the same set, adding up to 27 hard links to
  its stdlib zip (224 links mid-run against 197). On this base `nlink` reaches fuel (083's
  amendment). The count stayed three digits, and the repeats above, on an idle set, show a spread
  of the same size, so I do not think it explains the `cpython-c` value. I cannot rule it out
  completely either, so I name it. If the lane wants a clean reviewer record for this row, the
  `cpython-c` node alone, serial, on a fresh private set is a 5-minute run.

## Findings, most severe first

### F1 (fix before landing): a killed judge leaves every run's stdlib folder sealed, and `rm -rf` and `git worktree remove` then fail

- **What happens (EXECUTED, section 4).** `guest.run` seals each run's `lib` (pre-build F4's fix),
  and the `guest` fixture's run folders stay until the session ends. So a SIGKILL or SIGTERM
  leaves one sealed folder per run so far, not just the stages and mpl-data: 27 after 75 s of two
  check files; a full judge killed late would leave hundreds.
- **Why it matters.**
  - `rm -rf build` and `git worktree remove` fail on them. Both are routine here: agents stop
    background judges (the builder did, the "stray full-suite run"), and the lane removes
    worktrees.
  - Each leftover `lib/python315.zip` is a hard link to the set's zip on this base. Before 089,
    `rm -rf` cleared them; now it cannot, so a shared set's link count stays raised, and 083's
    amendment measured that count reaching fuel (spec 039's lesson, made stickier).
  - Decision 3 says "a killed judge leaves its stages sealed". It leaves much more.
- **Fix.**
  1. In `guest.run`, unseal `lib` once the run has ended, in a `finally` around the run and
     `watch.after()`: `litter.unseal(lib)`. It is never read again, and unsealing changes nothing
     a guest sees (removing it would: on this base the zip's link count reaches fuel, so leave the
     removal to 083). A kill then leaves at most one sealed `lib` per live run, plus the stages
     and mpl-data.
  2. Correct Decision 3's sentence to name what a kill leaves.
  3. Optional, and cheap: at session start, count folders under `paths.HARNESS_TMP` without the
     owner's write bit and print one line with the recovery (`chmod -R u+w build/harness`), never
     unsealing them. That keeps Decision 3's no-sweep argument and makes the recovery visible
     where it is needed. A lock-keyed sweep (section 4) is the stronger alternative.
  4. A unit row: a sealed `lib` is unsealed after a run that raises (a `Watch` failure).

### F2 (fix before landing): 083's rebase must remove `lib` through `litter.remove`, not only order the watch first

- **The merge (EXECUTED).** `git merge-tree --write-tree 6f525a0 e0bb460`: one conflict, in
  `tests/harness/guest.py`, one hunk: 089's `watch.after()` and `return Result(` against 083's
  `result = Result(`. `test_v1_4_embedding.py` merges cleanly. Textually it is trivial.
- **Semantically it is not.** 083's `_release(store, lib)` does `store.close()` and then
  `shutil.rmtree(lib, ignore_errors=True)`. On a folder 089 sealed, that removes nothing and says
  nothing (EXECUTED, `probes/release_on_sealed.out`: "lib still there after 083's _release:
  True ['python315.zip']"; `litter.remove` then takes it). So after a naive rebase each run's
  private stdlib copy stays until the session ends, against 083's Decision 10 ("one copy per live
  run, never one per run of a session"). On darwin it is an APFS clone; on Linux and in CI it is
  a 22 MB copy per run.
- **Fix.** 089's Depends-on line (and Disposition F7) adds: in 083's rebase, `_release` removes
  `lib` with `litter.remove(lib)` after `store.close()`, and `watch.after()` runs before it inside
  the `try`/`finally` that still releases. If F1's `litter.unseal(lib)` is added, the rebase folds
  it into `_release`. The lane checks this in 083's delta review.

### F3 (fix before landing): "For the lane" expects grew 0, and says nothing about a CPython row that crosses the tolerance on main's own noise

- **What happened (EXECUTED).** My full judge is red on `cpython-c` (+1.21e-4). The repeats in
  section 5 show main `3866f56` and 089 spreading the same way (up to +8.5e-5 on main in three
  runs), so I find no sign that it is 089's.
- **The gap.** "For the lane" says "No `--accept-growth`: nothing grows" and, if a row moves, to
  compare with main first. It does not say what the lane does when main moves the same way.
  Worse, `sameness.py` compares my `-n 3` record with the lane's serial one at the same 1e-4: if
  the lane's `cpython-c` lands near the accepted value, the two records differ (1.2e-4 apart), and
  rule 6a stops the landing with no re-run allowed. That is a real chance on this base, through no
  fault of 089.
- **Fix.** Add to "For the lane":
  - If a CPython group (`cpython-a`, `-b`, `-c`, `-fs`, `-archives`) grows past the tolerance and
    main `3866f56` on the same private set shows a spread that covers it, the lane accepts with
    `--accept-growth "<row>: this base's own noise before 083 (spec 089 F8), main 3866f56 gave
    <values> on the same set"`, and records the main runs.
  - A sameness difference confined to those five rows, with main's spread covering it, is that
    same noise, not a judge finding; say whether the owner allows the landing on that ground, or
    whether 089 waits for the lane to judge both records on one run of main. Either way, say it
    before the lane meets it.

## Notes (no action needed to land)

- **N1. Two writers have no `refuse`.** `mpl_data_dir`'s `extractall` and `_place`'s `copytree`
  (a stdlib folder) feed sealed folders, so `seal` would delete a litter-named member of either
  without a word. Today the stdlib zip (2,421 members) and the inner `matplotlib/mpl-data.zip`
  (204) hold none (EXECUTED). Fix when convenient: refuse each inner member name before
  `extractall`.
- **N2. Say what is detection-only, and what is not watched.** Decision 2: a check's own read-only
  preopens are watched, not sealed. Intent: `Turns` and the product runner's runs are neither
  sealed nor watched (as Decision 4 and Scope already say).
- **N3. The void-run rule.** It is sound: a `HostLitter` failure is a red run that measured
  nothing, not a sameness difference, so rule 6a does not apply to it. Two details: the re-run is
  a whole fresh judge, not the failed checks alone; and the rule interprets an AGENTS rule inside
  a spec, so the owner's agreement belongs in the landing notes (or a line under rule 6a, later).
- **N4. A partial upstream stage stays unsealed.** If one package's `_prepare` raises (a refused
  member), `self.prepared` is no longer empty, so `seal` never runs for that session; later checks
  fail on "no source tree", loudly, so nothing is measured on it. No action.

## The full judge (EXECUTED)

- `uv run pytest -n 3` in the worktree at `6f525a0`, clean, 19:05:54 to 19:14:59, against my
  private set:
  - `wasi_python v1: 525/625 pass · 77 gap · 23 blocked · 0 fail (unit suite 1597/1605, 8 skipped)`
  - `ratchet vs b91e0eaa4e: lost 0 · absent 0 · unrun 0 · unrun locally 21 · gained 2 · grew 1 ·
    judge changed`; `GREW …[cpython-c]: fuel 372458058296 -> 372503229930`; `RED: 1 metric(s)
    grew`.
  - `2122 passed, 31 skipped, 77 xfailed in 544.26s`.
- `sameness.py build/089/latest-full.json build/089-review/latest-full.json`: no difference,
  exit 0. Judge hash the same in both.
- The record: the worktree's `build/089-review/latest-full.json` (= `build/progress/latest.json`),
  and the copy for the lane at
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/089-buildreview/reviewer-latest.json`.

## Tool calls refused

- One command that would have run `rm -rf` on a scratch path built from a shell variable was
  refused by the session's safety check. I did not retry it; the folders it would have cleared did
  not exist, and I created them with `mkdir` instead. Nothing depends on it.

## Verdict

**Lands once F1 to F3.**

- F1 is a `finally` with `litter.unseal(lib)` in `guest.run`, a unit row, and Decision 3's
  sentence. It moves no fuel.
- F2 and F3 are sentences: F2 in the Depends-on line, for 083's rebase; F3 in "For the lane".
- The seal and the watch are right. They are fuel-neutral (sameness finds nothing between two
  full judges), they fail closed on every host, and the Windows branch passes when simulated.

In one line: the seal and the watch hold and move nothing, but a killed judge now leaves sealed
run folders that defeat `rm -rf`, 083's rebase must remove `lib` through `litter.remove`, and the
lane needs a written rule for a CPython row that crosses the tolerance on this base's own noise.
