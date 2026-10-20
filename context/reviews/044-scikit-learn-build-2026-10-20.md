# Review of 044 — scikit-learn (the build review)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude), not the author or builder of 044 or 038; it reviewed none of
  044's or 038's earlier stages.
- **Reviewed:** `git log ecc2423..4a087fa` on `spec/044-scikit-learn` (stacked on 038's `ecc2423`,
  on main `958a22b`); last code commit `026ba56`, `4a087fa` README and context only. 038's commits
  are under their own delta review and are not read here.
- **Time box:** 45 minutes of reading (a package, build-class), plus the wait for CI.
- **Run:** 39418201520 (release workflow on `spec/044-scikit-learn`, head `4a087fa`; same code as `026ba56`)
- **Re-ran:**
  - `uv run pytest -q tests/unit/test_sklearn_build.py
    "tests/checks/test_v1_3_default_profile.py::test_scikit_learn_modules_are_builtin[plain]"
    tests/checks/test_v1_1_artifact_set.py::test_scikit_learn_notice_carries_its_bundled_parts`
    in the 044 worktree on its `build/artifacts` (`SHA256SUMS` `dc6ba3a5`), `build/lane.lock`
    absent → 12 passed, exit 0; the compiled-objects case ran (the SDK is unpacked), no skip.
  - The weak-duplicate gate's inputs, rebuilt read-only from the worktree's `build/`: the same
    archive list step 60 forms (the 237 module archives under `build/link/archives` plus every
    `.a` the `.deps` files name, scipy's shims, zlib, bz2, lzma, sqlite3), read with the SDK 34
    `llvm-nm -A -P -g --defined-only`, and classified with `scripts/weak_duplicates.py`'s own
    `findings`, `scope` and `allows` (scratch script outside the tree) → 0 unreviewed, 0 stale,
    the same as `build/link/weak-duplicates.log` (270 archives, 21,962 weak names). 1,495 names
    are shared across archives with one weak copy at least: 369 by the std/runtime rule, 1,126 by
    the 19 patterns (pybind11 563 + 13 + 1, xsf 404, Faddeeva 8, HiGHS 50 + 21 + 27, agg 22, mpl
    6, the five path_converters classes 6, `check_trailing_shape` 2, `_ZTSA19_c` 1, f2py 2).
  - `build/044/growth-vs-038.txt` and `build/044/fast-tier-2.log` read; the flags scanned for
    `"`, `$`, backtick and `!` (none) and for their `044:` prefix (all three).

## Acceptance criteria against evidence

1. **Checks seen failing first** — met, with L2 below: the golden, the four behaviour checks, the
   notice check, the images check, the unit checks and the constructor list are recorded in the
   builder's notes (READ). The weak-duplicate gate's item is met by the compiled-objects unit case
   (EXECUTED here: it names `bounded` in two archives and passes with one renamed) and by the
   first real link's 1,186 findings (READ), not by a real build without `_newrand`'s header; see
   L2 for why that item cannot name `bounded_rand_int` as written.
2. **The build** — met (READ, and EXECUTED in part): step 60's logs in the worktree show the gate
   (0 unreviewed, 0 stale), the link map (4 required, 3 forbidden, 0 findings) and the
   constructors (158 reviewed, none new); 69 modules; `MANIFEST` names the pin and recipes.
3. **Same bytes everywhere** — met (EXECUTED in CI): both rebuilds, the same bytes from every host, and the zero-patch step
   with 26 trees pass in 39418201520 and in 39416371904.
4. **The judge** — met for this stage: the fast tier `-n 3` on `026ba56` is 629/769, 0 fail, RED
   on growth only (READ, `build/044/fast-tier-2.log`); the lane's `--accept` is the lane's.
5. **The numbers recorded** — met (READ): sizes, members, modules, renames, constructors, fuel on
   both binaries, the native subset's counts, question 80's answer.
6. **The release** — met for this stage: every job passes but three macOS judges, red on growth lines only, in
   both runs; the wave's dry run on its tip is the lane's.

## Findings, most severe first

No High; one Medium.

1. **M1, one grown row is not claimed: `test_upstream_suite[cpython-fs]`**
   (`044-scikit-learn.md`, *For the lane*, "Rows that grow" and `--accept-growth`) — on macOS's
   upstream shard the row grew 62,994,222,641 → 63,099,389,920 against main in the builder's run
   39416371904; 038's own run 39415728849 on `ecc2423` has it at 63,023,374,266, so 044 adds
   **+76,015,654 fuel (+0.12%)**. The claim list counts 185 rows from the fast tier, which never
   runs the upstream suites, and the flag ends "no other row moves". The cause is almost
   certainly the same one, the 411 members' directory entries paid on the suite's starts and
   zip reads (INFERRED: about seven plain starts' worth), but the claim does not say so, and
   the checklist ranks an unclaimed changed row Medium. Closing evidence: the claim list names
   the row with these two numbers and its cause, and `--accept-growth` drops "no other row
   moves" or adds "cpython-fs +76 M by the same entries" (context only; the reviewer confirms
   against 39418201520's number).
2. **L1, the self-check's CI line is a template** (`context/specifications/044-scikit-learn.md`,
   *For the lane*, the self-check's second item) — it reads "run @RUN@ on `026ba56`
   (@RUNLINE@)", unfilled. Fix text: "run 39416371904 on `026ba56` (red: macOS own-guest 180, own-embedding 33 and upstream-macos 1 GREW, 0 lost, every other job green)".
3. **L2, criterion 1's gate item cannot hold as written; answer it in writing**
   (`044-scikit-learn.md`, acceptance criterion 1 and the notes) — "the weak-duplicate gate
   against a build without `_newrand`'s rename header (it names `bounded_rand_int`)". On this
   build `bounded_rand_int` is inlined in all three copies and absent from `llvm-nm` of
   `sklearn_svm__newrand.a`, `liblibsvm-skl.a` and `libliblinear-skl.a` (EXECUTED); and with only
   one header missing, only one copy keeps the original names, so there is no duplicate to name.
   What does stand behind the renames: `mt_rand` (D) and `set_seed` (T) are strong in each copy,
   so two un-renamed copies are wasm-ld's `duplicate symbol` and step 60's `clashes()`; one
   un-renamed copy is the link map's `--forbid mt_rand set_seed`; the gate covers a weak copy
   that survives `-O`. Fix text for the landing notes: "Criterion 1's gate item is met by the
   compiled-objects unit case and the first link's findings. On this build `bounded_rand_int` is
   inlined everywhere; a missed rename is wasm-ld's duplicate `mt_rand`/`set_seed` (two copies)
   or the link map's forbid (one copy)."
4. **L3, `packages.toml` names 066, the roadmap reserves 095** (`tests/upstream/packages.toml`,
   `[package.scikit-learn]`, `closes_with = "spec 066"`) — the roadmap on main (Reserved line)
   reserves 095 as "the closer `tests/upstream/packages.toml` names for 037, 038 and 044 in place
   of 066". Fix: `closes_with = "spec 095"`, and the self-check's packages.toml item to match; or
   a line in the landing notes saying 066 stays until 095 rewrites scipy's and scikit-learn's
   rows together. A judge file, so the builder's change, under `--accept-judge`'s list.
5. **L4, the native test script cannot see a group that dies**
   (`tests/jobs/oracle/sklearn_native_tests.sh`, `group()` and the final grep) — each group runs
   `|| :` and the script fails only on "N failed" or "N error(s)" in the outputs. A group whose
   interpreter aborts (a crash in a native module, an OOM kill) prints no summary line and
   counts as passed. Fix: record pytest's exit status per group and fail on any non-zero, or
   require the last line to match `[0-9]+ passed`. The recorded counts (6,115 passed, each group
   with a summary) are unaffected; this is not in the release.

### Notes (no change needed for landing)

- **N1, the std:: rule can hide a user-type ODR clash in principle.** `allowed_by_rule` allows
  every name whose outermost scope is `std`, so `std::vector<Node>::push_back` for two packages'
  different `Node` would merge silently. Today it hides nothing: every cross-package std:: name
  in this link is instantiated over std, builtin, CPython (`_object`, `_typeobject`), pybind11 or
  HiGHS types, and the HiGHS ones are `libhighs.a` against scipy's own binding modules, one source
  (EXECUTED, the scratch classification). A later narrowing: allow std:: by rule only when no
  template argument names a type outside std, the builtins and an allowed scope.
- **N2, intra-archive duplicates are out of the gate's view by design** (its docstring and unit
  case say so). Every scikit-learn generator copy sits in a different archive
  (`_newrand`'s module archive, `liblibsvm-skl.a`, `libliblinear-skl.a`), so the motivating case
  is in view.
- **N3 (the confirmation's N3), the 19 patterns read one by one.** Each reason's facts check
  against the build: the thirteen `extern "C" inline` slots at `pybind11/detail/class.h:50` to
  `:726` with `pybind11_meta_dealloc` at `:209`, in exactly the fourteen modules named; one
  pinned pybind11 wheel unpacked by steps 55 and 57; `_ZTSA19_c` only in `_backend_agg` and
  `ft2font`; the f2py pair only in `_fblas` and `_flapack`; the HiGHS scopes only in `libhighs.a`
  and scipy's two binding modules; the agg, mpl, path-converter and `check_trailing_shape` names
  only in matplotlib's modules; xsf and Faddeeva only in scipy. No pattern matches a name that is
  strong in one archive and weak in another, so no allowed name overrides a strong definition.
  No allowed cross-package name carries a scikit-learn type. Three wording points, for the next
  touch of the file (it is hashed in `MANIFEST`, so not worth a rebuild now):
  `scope:pybind11_meta_dealloc` is redundant (its one name also matches `pybind11_*` through the
  demangled form, and the stale check cannot see a redundant pattern); `pybind11_*` could be the
  thirteen exact names; and `scope:pybind11`'s "same flags" is not literal (scipy force-includes
  `scipy_rename.h` and adds WASI emulation defines, matplotlib adds `-fexceptions`), though none
  of these touches pybind11's code and all are `--buildtype=release` with `b_ndebug=if-release`.
- **N4, `--against` on a clean build does not see step 60's own builtins.** On the first run of
  step 60, `Modules/config.c` is CPython's own and lacks `_host`, `zlib`, `_bz2`, `_lzma` and
  `_sqlite3` until the Setup.local below it regenerates it; a package module with one of those
  init names would pass the gate. None exists. B11's gate is otherwise sound: it compares the
  final (renamed) init names with every `PyInit_*(` declaration in config.c, the package-to-package
  clash check stays, the unit check was seen failing (READ) and passes here (EXECUTED), and no
  `PyInit_` name is defined twice across the link's archives (EXECUTED).

## Focus items

1. **The weak-duplicate gate** — sound for what it claims; the 19 patterns read (N3); no hidden
   ODR collision today (N1); scikit-learn adds no pattern.
2. **B11** — the rename is right (`utils_random.h`, the RENAMED row, the include map's tenth
   entry); `--against` is sound with N4's edge; seen failing (unit), passing on the build.
3. **The native-tests script** — moved under `tests/jobs/oracle/`, confined under
   `build/sklearn-native/` with HOME, caches and data redirected, network tests skipped, hashes
   required, one thread; L4.
4. **Constructors** — exactly the three Decision 8 names, each the renamed `std::mt19937`, with
   their reasons in `tests/harness/constructors.py`; the link's check says none new.
5. **B1** — `LICENSES/scikit-learn.txt` in the built set carries `_tree.pxd` lines 1-28 (Leland
   McInnes, BSD-3-Clause), `_split.py` lines 1001-1015 with the full Apache-2.0 text from
   wasi-libc's pinned `LICENSE-APACHE`, `_testing.py` lines 575-577 and pytest's MIT text
   (`pytest-0d90a31d-LICENSE`) (EXECUTED); the owner's approval is on main, `decisions.md`,
   "Three answers for 0.1.0 (2026-10-20)" (READ).
6. **Claim list against the fuel rows** — M1 (`cpython-fs`, an upstream row the fast tier cannot see); otherwise 185 fuel rows up, 0 down, median +1.856%; the three
   byte rows +9,002,368, +9,157,787 and +3,281,762 (EXECUTED from the growth file);
   `test_guest_runs_here[plain]` +11,195,663 = 27,240 per member, inside 30,000;
   `[snapshot]` +1,048,559; the two outliers explained. The growth file also shows 038's Sobol
   check moving fail → pass, 038's fix, not 044's claim. Flags: paste-safe, each begins "044".
7. **Spec 063** — `packages.toml` has its line (`later`), with L3 on the closer.
8. **README and CHANGELOG** — 22 carried patches in the table, the prose and the build section,
   22 `.patch` files on the branch (EXECUTED); the CHANGELOG entry under "0.1.0a8 — unreleased".

## CI

Both runs, read back with `gh run view <id> --json jobs` and `--log-failed`. `gh run download
<id> -n release-record-1` finds no artifact in either: "gather the shards' records" is skipped
when a judge job is red, so the record was read from the jobs' logs instead.

- **The reviewer's run 39418201520** (dispatched on the branch, head `4a087fa`, the same code as
  `026ba56`; it queued behind the builder's run through the workflow's `release-<ref>`
  concurrency group): both Linux rebuilds, macOS's build and judge, the same bytes from every
  host, the three verify jobs, every Windows judge (own-guest, own-embedding, own-runner,
  upstream-windows), and every Linux shard **pass**. Red: three macOS jobs, **growth only**:
  - own-guest: 498 passed, 4 skipped; ratchet lost 0, gained 23, grew 180; `RED: 180 metric(s)
    grew`.
  - own-embedding: 178 passed; lost 0, grew 33; `RED: 33 metric(s) grew`.
  - upstream-macos: 4 passed, 36 xfailed; lost 0, grew 1, `GREW
    test_upstream_suite[cpython-fs]: fuel 62994222641 -> 63099389920` (M1).
- **The builder's run 39416371904** on `026ba56`: the same jobs green and the same three red,
  with the same counts and the same `cpython-fs` number to the unit. No G7 line and no lost pass
  in either run. Every red line is a growth line.

## Constitution checks

- §4.1 upstream patches: one, recorded, hashed in `MANIFEST`, drafted under
  `context/upstream/patches/scikit_learn-1.9.1/`; the renames are recipe headers. Holds.
- Every input pinned: the sdist and pytest's, numpydoc's and django's licence texts in
  `SHA256SUMS`. Holds.
- uv only; prior art not copied; artifacts out of git; tests count fuel, not time. Hold.
- Downloads run only as build tools or under wasmtime: the native-tests script runs the sdist's
  tests on the host, confined as the oracle is (the confirmation's N1 accepted this); not a build
  step.
- §7 never-do: nothing tripped; no judge file edited to turn a run green (the judge changes are
  listed under `--accept-judge`).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. M1 — fixed in the specification (*For the lane*, the claim list's new bullet and
   `--accept-growth`; context only): `test_upstream_suite[cpython-fs]` is claimed with its numbers,
   63,023,374,266 in 038's run 39415728849 to 63,099,389,920 in 39416371904 and 39418201520
   (+76,015,654, +0.12%; main 62,994,222,641), and "no other row moves" is gone. The cause, by
   reasoning from the records without a rebuild: the same 411 members, but paid where the suite
   rebuilds the stdlib zip's directory, not at starts. The group runs in one snapshot session
   (`tests/harness/upstream.py`), whose start costs +1.05 M; `zipimporter.invalidate_caches()`
   drops the zip's `_zip_directory_cache` entry (`Lib/zipimport.py:228-230`), so after each
   `importlib.invalidate_caches()` the next import rebuilds the directory over every member, and
   one rebuild costs +36.2 M more with the 411 members
   (`test_the_fast_reader_builds_zipimports_dict[snapshot]`, 481,672,302 to 517,853,643). So
   +76.0 M is about two rebuilds plus the start (INFERRED; the rebuilds were not counted). This
   corrects "about seven plain starts": the group starts once, on the snapshot.
2. L1 — fixed: the self-check's CI line names 39416371904 on `026ba56` and this review's
   39418201520, both red only on growth (own-guest 180, own-embedding 33, upstream-macos 1; 0 lost;
   no G7).
3. L2 — answered in writing in the landing notes ("The weak-duplicate gate's seen-failing item"),
   with the review's fix text: criterion 1's gate item is met by the compiled-objects unit case
   and the first link's findings; `bounded_rand_int` is inlined everywhere; a missed rename is
   wasm-ld's duplicate `mt_rand` or `set_seed` (two copies) or the link map's forbid list (one
   copy).
4. L3 — fixed: `tests/upstream/packages.toml` names `closes_with = "spec 095"` for scikit-learn,
   with a comment; the self-check's item and the B6 note match; `--accept-judge` names it.
5. L4 — fixed: `tests/jobs/oracle/sklearn_native_tests.sh` records each group's exit status and
   fails a group unless pytest exits 0 and its last line counts passed tests. The script has no
   unit check of its own; the group logic was exercised with stubs (passed, failed, a fatal abort
   at exit 134, no tests at exit 5: only the passed group counts as passed), and `sh -n` passes.
   Not in the release, so no CI rerun.
6. N3's wording points — recorded in the landing notes for the next touch of
   `recipes/weak-duplicates-allowed.txt`; no change now.

## Verdict

Lands once M1 is closed: the claim list and `--accept-growth` name `cpython-fs`'s +76.0 M over 038's
run, with its cause. L1 to L4 are write-ins needing no further round.
