# Review of 099: numpy's own floating-point signals are kept in software, so a singular matrix raises `LinAlgError` (the confirmation of M1's answer)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), not the author. It did not write 099, did not review it before the build, and did not do its build review.
- **Reviewed:** `spec/099-numpy-singular-inverse` at `b6238c0`, on main `2516875` (wave 07). The answer to M1 is `4fac7e2`. The rebuild and its facts are `6866dd1`. `b6238c0` fills in the Disposition and re-derives the claim list. The code diff is `2516875..b6238c0`. The build review reviewed `f7448c7` on `3ff1871`.
- **Time box:** 30 minutes for a confirmation of one Medium finding, plus reading the run back.
- **Run:** 39454475153 (run 125), the builder's run on `6866dd1`. Read back under the owner's rule of 2026-10-20 (main `30e9b41`, constitution §5.6), not dispatched again. `b6238c0` differs from `6866dd1` only in two `context/` files (EXECUTED, below). The build reads neither. The rules checks that read `context/` were run locally on `b6238c0` instead (below).
- **Re-ran (EXECUTED, `build/lane.lock` absent each time, single node ids only, no build, no tier):**
  - `git range-diff 3ff1871..f7448c7 2516875..b6238c0`: commits 1 to 8 are `=`, and 9 to 11 are new (`4fac7e2`, `6866dd1`, `b6238c0`).
  - `git diff 4fac7e2 b6238c0 -- . ':!context'` is empty, and so is `git diff 6866dd1 b6238c0 -- . ':!context'`.
  - The code diff against main, compared with the reviewed code diff (`3ff1871..f7448c7`), line for line: the only changes are the header's three comment lines and the allow-list's three lines.
  - `git merge-tree --write-tree 30e9b41 b6238c0` merges cleanly. Main's newest commit touches only `AGENTS.md`, `context/constitution.md`, `context/decisions.md` and `context/roadmap.md`.
  - Step 60's gate, rebuilt by a scratchpad copy of step 60's archive-list logic and run with the branch's own `scripts/weak_duplicates.py` (`uv run python -I`):
    - with the branch's allow-list: `270 archives, 21964 weak names, 0 unreviewed, 0 stale patterns`, exit 0;
    - with the entry removed: `weak definition shared by 17 archives: wasi_python_fe_flags: …` and `1 unreviewed`, exit 1.
  - `llvm-nm` on every archive in the worktree's `build/`, both packed and thin. 177 objects define `wasi_python_fe_flags`. Every definition is `W`, 4 bytes, in a `.bss.wasi_python_fe_flags` segment, and all 177 were counted one by one. Nothing outside numpy defines the name, weak or strong. Two objects were read with `llvm-objdump -t`, a C one and a C++ one: `w O DATA 00000004 .hidden wasi_python_fe_flags`.
  - `build/link/python.map` names the word once: `19eeed8 0 4 …numpy__multiarray_umath.a(src_multiarray_dragon4.c.o):(.bss.wasi_python_fe_flags)`.
  - The spec 100 worktree (`702291c`, read-only) was checked the same way. Its 13 module archives and 4 numpy static libraries define the word weakly. `libopenblas.a` and `libnumpy_lapack_shims.a` do not define it.
  - Node ids in the 099 worktree: `tests/unit/test_sklearn_build.py`, `test_a_singular_matrix_raises_linalgerror[plain]` and `test_every_numpy_compile_keeps_its_floating_point_flags_in_software` → 12 passed, exit 0, `grew 0`.
  - Node ids on `b6238c0`, five `test_rules.py` nodes that read `context/` or the README: `test_specifications_have_their_header_and_sections`, `test_specifications_have_no_open_question`, `test_landed_specifications_cite_an_existing_review`, `test_the_version_is_released_by_the_book` and `test_the_readme_carries_the_licences_credit_lines` → 5 passed, exit 0.
  - The worktree's `build/progress/latest.json` was backed up before each node run and restored after. Its SHA-256 is `858f11c9…` again, and `git status` is clean.

## The answer to M1 against what closes it

The build review's M1 asked for four things.

1. **The list entry with its reason, or a single definition:** met (READ and EXECUTED). `recipes/weak-duplicates-allowed.txt:60` lists the exact name with no wildcard. Its reason is on the same line. The gate's own reader accepts it, and the gate passes with it and fails without it (EXECUTED).
2. **A build from empty that passes step 60's gate:** met (READ and EXECUTED). `build/099/build-07.log`: 19 steps, exit 0, ended 11:53. `4fac7e2` was committed at 11:40. `build/logs/60_link.log` holds the gate line `weak duplicates: 270 archives, 21964 weak names, 0 unreviewed, 0 stale patterns`, and the reviewer reproduced it.
3. **`python.map` showing one definition:** met (EXECUTED). There is one segment and one symbol, at `0x19eeed8`, 4 bytes, from `dragon4.c.o`.
4. **A new dry run read back, with the claim list and the flags re-derived:** met (EXECUTED, below).

## Acceptance criteria against evidence (what the rebase and the fix could move)

1. **Nothing changed but the rebase and the named fixes:** met (EXECUTED). The range-diff and the line-for-line diff above show it. `build/099/rebase-07.log` shows 8 of 8 commits replayed with no conflict.
2. **`b6238c0` touches only `context/` after `6866dd1`:** met (EXECUTED). It changes the build review, where only the Disposition is filled in (`git diff -U0`: it adds lines and removes only the three empty `M1 —`, `L1 —` and `L2 —` placeholders), and the specification.
3. **The set's facts:** met (EXECUTED).
   - `SHA256SUMS` hashes to `5f2032421ed4…` in the worktree. CI's Linux rebuild artifact (`rebuild-ubuntu-24.04`) gives the same hash. Main's set is `dc6ba3a5a122…`.
   - `python.wasm` 93,793,855 → 93,793,595 bytes (−260). The snapshot 98,620,293 → 98,620,033 (−260). The zip 47,730,899 → 47,730,914 (+15).
   - CI's macOS build and both Linux rebuilds print `python.wasm 93793595 bytes ee45b2410a0de71b`, the same as the local build.
   - `MANIFEST` differs from main's in exactly four lines: `recipes/npy_fenv_flags.h` added, `recipes/wasi-numpy.cross` changed, `recipes/weak-duplicates-allowed.txt` changed, and `x-snapshot-zip`. Each recipe hash matches the file on the branch. `LICENSES/` is identical (`diff -rq`).
   - **Only numpy's 19 archives differ:** met as worded (EXECUTED).
     - Of the 237 module archives in `build/link/archives`, exactly numpy's 13 differ from main's by hash.
     - The six numpy static libraries named by `.deps` files differ too: `lib_multiarray_umath_mtargets`, `lib_simd_mtargets`, `lib_umath_tests_mtargets`, `libnpymath`, `libunique_hash` and `libnpyrandom`. That makes 19.
     - Outside `link/archives`, the other differences are intermediate archives that hold a path: `scipy-build/scipy/lib_fortranobject.a` is a 634-byte thin archive whose member path names the worktree, and CPython's `libpython3.15.a` and `_hacl` archives embed the build path, being 84 bytes larger for the worktree's longer path. None of them is a module archive. The final binary is the same on every host (above).
4. **The run read back:** met (EXECUTED).
   - `headSha` is `6866dd16…`, the event is `workflow_dispatch` and the run number is 125.
   - 24 jobs passed, 4 were skipped (gather, attest, publish release, publish wheel), and 1 was red: `judge (macos-15, own-guest)`.
   - The red shard's log: `406/776 pass · 0 gap · 2 blocked · 0 fail` and `ratchet vs e9a76ce1aa: lost 0 · absent 0 · … · gained 7 · grew 22`, with no G7 line. `RED: 22 metric(s) grew` is its only red reason.
   - The shard's record (`record-macos-own-guest-failed-1`) was compared with the branch's `accepted.json` (`e9a76ce`) through `harness.scoreboard.compare`, the judge's own code: `lost 0, absent 0, fewer 0, gained 7, grew 22`.
   - Every one of the 22 grown rows is in the claim list, with the same percentage to four places. That is the zip (+15 bytes) and 21 fuel rows from +0.0109% to +0.0846%. `test_lxml_xml_job_matches_native` grew most, +20,433,123 fuel.
   - 099's six guest nodes pass in the macOS, Linux and Windows `own-guest` records. Check 4 passes in `record-build-build` with the reason `compiles 189, c 166, c++ 23, not compiles 9`.
5. **The flags:** met (EXECUTED). There are three lines. Each body begins `099`. None contains `"`, `$`, a backtick, `!` or a backslash. `--accept-growth` matches the record: the zip's numbers, "twenty-one rows up +0.0109% to +0.0846%", and all four `MANIFEST` lines (the build review's L2 is closed).

## Findings, most severe first

1. **L1 (Low): the allow-list's reason says "13 archives"; the gate sees 17** (`recipes/weak-duplicates-allowed.txt:60`).
   - **The defect.** The reason says `in every numpy object (13 archives)`. Step 60's gate reads numpy's 13 module archives and also the four static libraries their `.deps` files name: `libnpymath.a`, `libnpyrandom.a`, `libunique_hash.a` and `lib_multiarray_umath_mtargets.a`. With the entry removed, the gate prints `shared by 17 archives` (EXECUTED). That is 177 objects, all weak, 4 bytes, `.bss`. The 13 came from the build review's own run, which read only the module archives.
   - **It is not 100's count.** Spec 100's tree has the same 13 + 4 (EXECUTED). So the text is wrong for 099 as built, not only after 100.
   - **Failure.** No wrong behaviour follows, because the entry matches by name, not by count. It covers 099's 17 and spec 100's 17 alike. The failure is an audit one. A reviewer who checks the entry against the gate's output sees 17 where the reason says 13. They must then work out whether four archives joined without review, or else trust a count that is already wrong.
   - **A cosmetic slip in the same change.** The reflow in `recipes/npy_fenv_flags.h:15` left a 118-column line in a file wrapped at 100 columns.
   - **Fix text.** In `recipes/weak-duplicates-allowed.txt:60`, replace `in every numpy object (13 archives)` with `in every numpy object (numpy's module archives and the static libraries their .deps name: 17 of the link's archives at numpy 2.5.2)`. Rewrap `recipes/npy_fenv_flags.h:13-16` at 100 columns.
   - **Who carries it.** Both files are recipes whose hashes `MANIFEST` records. So the fix changes the set's `SHA256SUMS` and needs a rebuild, and that is the builder's work, not a write-in. A rebuild for two comments is not worth a new dry run of 099. The recommendation: spec 100 carries both edits on its rebase onto 099's tip, since it rebuilds from empty there anyway. 099's Disposition should say so in writing. The lane may instead have 099 carry them before the wave, if wave 08 rebuilds the set anyway. Either way, no further review round (§5.6).
2. **N1 (note): the shard's "gained 7" is not 099's seven nodes.** In run 125's macOS `own-guest` record, the 7 gained are 099's six guest nodes plus `test_v1_1_artifact_set.py::test_wheel_carries_the_artifact_set`. That check is absent from `accepted.json` because it is blocked locally for want of a wheel, and every CI run gains it. 096's notes say the same. 099's seventh node, check 4, passed in the build job. The claim list is right as written. Optional fix text for the *Landing notes* line on run 39454475153, after `grew 22`: "(the 7 gained there are 099's six guest nodes and `test_wheel_carries_the_artifact_set`, blocked locally for want of a wheel, not 099's; check 4 passed in the build job)".
3. **N2 (note): what a match by name leaves open, and why that is acceptable.**
   - **What stays open.** The entry allows any later definition of `wasi_python_fe_flags`, including a strong one or one of another size. The gate would no longer stop on it.
   - **Why it is acceptable here.**
     - The name carries the project's own prefix, and only one recipe header defines it (`grep` over `recipes/` and `scripts/`).
     - Check 4 holds every numpy compile to that header.
     - The gate's stale-pattern rule stops the build if the header is removed and this line is not. So the entry cannot outlive the header its removal sentence names.
     - All 177 copies are identical (EXECUTED), so it does not matter which one wasm-ld keeps.
     - `.hidden` visibility does not split the word in a static link. The map shows one definition, and the singular-matrix checks pass. They depend on a raise in `umath_linalg` and a read in another object seeing the same word.
   - **The rules and precedent agree.** The allow-list's rule forbids C-linkage entries "whose copies differ, or that keeps state of its own file". This word is neither: one shared object is the design. `_npy_f2py_ARRAY_API` (spec 037) is the precedent: weak C data, shared on purpose, allowed by name.
   - **Why not a single strong definition.** The build review also offered one. It is cleaner, but it would edit step 60, which spec 100 also edits. The builder's choice is the smaller change (§6.4). No action.
4. **N3 (note), for the lane: the base.** Main has moved from `2516875` to `30e9b41`, which touches only `AGENTS.md` and `context/`. The textual merge is clean (EXECUTED). Under the owner's rule of 2026-10-20, wave 08's rebase and dry run are the check, and 099 needs no new run.

## Constitution checks

- **§4.1:** there is still no patch. The adaptation stays a recipe file, and the allow-list line is a recipe file too. Holds.
- **Pins:** `downloads/SHA256SUMS` is unchanged (it is not in the code diff). Holds.
- **The artifact set and the guest's imports and exports (§5.6):** the set changes by the hash recorded in `MANIFEST`. The imports and exports are unchanged: `tests/public_api.txt` is not in the diff, and the `own-guest` shards' import checks pass. Holds.
- **Never weaken the judge:** no golden, gap, allowance, `tests/upstream/` file or progress file is in the diff. The allow-list is a build input, read by step 60. It is not a judge allowance. Holds.
- **Artifacts never live in git (AGENTS.md):** none is committed. Holds.
- **§7:** nothing tripped. This review dispatched no run, built nothing and wrote nothing to the builder's tree or branch.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1: carried by spec 100 at its rebase onto 099 / fixed in <commit> before wave 08.
2. N1: the optional clause written in / left as is.
3. N2, N3: no action.

## Verdict

Lands: M1 is closed by a name-exact allow-list entry whose premise holds (177 identical weak, zero-filled, 4-byte copies in 17 archives, one definition in the map), the rebase replayed unchanged, and run 39454475153 on `6866dd1` is red only on the 22 claimed growth lines; L1 is a comment to correct when the recipe is next rebuilt.
