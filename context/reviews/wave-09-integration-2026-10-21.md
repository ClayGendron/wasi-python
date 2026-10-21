# Review of wave 09's integration (100, 097)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of 100 or 097 and reviewed none of
  them before (their pre-build and build reviews were other agents'). It is the wave's
  integration reviewer (AGENTS.md rule 8; constitution §5.7).
- **Reviewed:** the wave's tip **`a68efbb`**, linear on main `58f108f` (the structural chain 103
  to 109 and the lane's three fixes): 100 (`58f108f..8e7eac9`, 12 commits), then 097
  (`8e7eac9..a68efbb`, 10 commits); no merge commit (EXECUTED: `git merge-base --is-ancestor`
  both ways, `git log --merges` → 0). The review began on the earlier tip `6fa6254` (100 at
  `d5c76bb`); after H1, 100 gained `8e7eac9` (the oracle lock's fix) and 097 was rebased onto it
  without a hunk. Sections 1 to 3 were done on `6fa6254`; section 1a reads what changed.
  `git diff --stat 6fa6254 a68efbb`: the lock (4+/2−) and the two specifications' notes, nothing
  else. Spec 101 is not in the wave (it waits for Docker).
- **Run:** the wave's dry run of record **39559520924** on `a68efbb`, read back in section 4; the
  earlier dry run **39555640193** on `6fa6254` (the same artifact set: no recipe or script moved)
  as supporting data. 100's own runs: 39535794638 on `186b9a4` (its restack onto the chain); 097's:
  39532775277 on `90eed13`. The chain's own run on `dbecd2d`, 39530569266, is the base for the
  deltas below.
- **Ran:** reads, and in a `git clone --shared` of the repository in this agent's scratchpad (no
  worktree, no branch switch in the main tree), at `6fa6254`: `uv run ruff check src tests` → "All
  checks passed!"; `uv run ruff format --check src tests` → "151 files already formatted";
  thirteen rules checks by node id (`test_code_outside_src_names_no_context_document`,
  `test_carried_patches_follow_the_rules`, `test_specifications_have_their_header_and_sections`,
  `test_specifications_have_no_open_question`, `test_landed_specifications_cite_an_existing_review`,
  `test_built_structural_specifications_cite_their_pre_build_review`,
  `test_src_names_no_context_document`, `test_no_embedder_name_in_code`, `test_no_test_reads_a_clock`,
  `test_build_scripts_call_python_only_through_uv_or_a_path`, `test_every_package_names_its_own_suite`,
  `test_no_artifact_or_large_file_is_tracked`, `test_executed_memos_label_their_claims`) → 13
  passed; the unit files `test_scan.py`, `test_host_litter.py`, `test_build_scripts.py`,
  `test_scipy_build.py`, `test_plugin.py` → 367 passed; `test_one_lapack_is_linked` → blocked
  (compile records, none in a clone) and `test_the_judges_writable_roots_are_outside_the_home_folder`
  → passed; `--collect-only` of `tests/unit` and `tests/checks` at `58f108f`, `d5c76bb` and
  `6fa6254`. CI records of runs 39535794638 and 39530569266 downloaded with `gh run download` into
  the scratchpad and compared row by row against `context/progress/accepted.json` at `58f108f`
  (`predict.py`, `delta.py`, the ratchet's own rule: fuel past 1e-4, bytes past 0). No judge tier
  ran; no build ran; nothing was dispatched. `build/lane.lock` was absent when I started.
- **Box:** 45 minutes for the reading, plus the wait for the dry run.

## 1. Each entry's rebase against its reviewed diff (EXECUTED)

Method: `git diff <old base> <old tip>` against `git diff <new base> <new tip>` per file, `index`
and `@@` lines dropped, compared line by line; then the added and removed lines alone, comment
lines (`#`) dropped, compared again, so a docstring or code line that differs stands out; and
`git range-diff` beside it.

### 100 (`b0e1593..702291c`, its build review's range) against `58f108f..d5c76bb`

`git range-diff`: the six reviewed commits map one to one (`237e6d8`→`18f62d6`,
`74834e0`→`5250d2d`, `109ee2d`→`2effc96`, `702291c`→`8f8e0ed` identical; `8826d72`→`4035195` and
`664e183`→`bd4a3fb` changed, the rebase hunks), then five commits no review read: `cb397b1` (the
build review, copied), `0babe58` (restack onto wave 08), `74056c3` (the 26 citations reworded for
109's rule), `a93e8e9` (rebuilt from empty: context, README, CHANGELOG), `d5c76bb` (rebased onto
main, notes only).

The file list differs by the build review file, the five `restack-*.txt` evidence files and two
recipe files (`npy_fenv_flags.h`, `weak-duplicates-allowed.txt`). Per file, outside `context/`:

| file | interdiff lines | what they are | verdict |
|---|---|---|---|
| `recipes/numpy_file_includes.txt`, `numpy_lapack_abi.h`, `numpy_lapack_shims.c`, `wasi-numpy.cross`, `tests/jobs/oracle/uv.lock` | 0 | — | identical |
| `scripts/steps/60_link.sh` | 46 | the header comment (named conflict: the chain's wording plus "scipy and numpy with one OpenBLAS"); 044's step 58 precondition kept above 100's shims check (named conflict); the comments' citations dropped (74056c3); **one code line**: `weak_archives` gains `$B/numpy-shims/libnumpy_lapack_shims.a` and its comment "scipy's and numpy's shims" | clean: (a), (b); the code line is the build review's L6, read below |
| `scripts/steps/40_numpy.sh` | 17 | the header comment (named conflict) and three comments without their spec numbers | clean: comments only |
| `scripts/wasi-cc` | 4 | two comments without spec numbers | clean |
| `recipes/npy_fenv_flags.h` | 15 | a comment rewrapped (099's confirming review's L1, named in the restack notes) | clean: comment only |
| `recipes/weak-duplicates-allowed.txt` | 9 | `wasi_python_fe_flags`' reason text, "13 archives" → "numpy's module archives and the static libraries their .deps name: 17 …" (099's confirming review's L1) | clean: the gate reads only that a reason exists (READ, `scripts/weak_duplicates.py:99-109`) |
| `tests/harness/scan.py` | 43 | four docstrings without citations; the rest is context (the chain's `tokenize`/`warnings` imports and citation-file collector beside 100's section, the named conflicts) | clean: added/removed lines equal but for docstring text |
| `tests/checks/test_v1_3_data_stack.py` | 42 | one comment block and three docstrings reworded | clean |
| `tests/checks/test_v1_5_rebuild_from_pins.py` | 6 | two docstrings reworded (one an unrelated line of context, `line.conf`'s, which the chain changed) | clean |
| `tests/unit/test_scan.py` | 10 | context (main's `npy_fenv` rows and the chain's citation rows above 100's ten) and one comment | clean |
| `tests/jobs/oracle/pyproject.toml` | 2 | one comment | clean |
| `README.md`, `CHANGELOG.md` | 20, 18 | named conflict hunks and the re-measured numbers (1,240,316 / 1,237,935 bytes; "28 percent"; the sizes row 92.6 / 97.4 / 49.8 MB) | clean: (a), (b) |

With comment lines removed, the added and removed lines of the six code files are identical to the
reviewed diff's but for docstring wording and the one `weak_archives` line (EXECUTED).

**L6's fix, read against the finding** (§5.6: a fix to code for a Low is read by the lane at the
landing; I read it for the lane). The line at `d5c76bb:scripts/steps/60_link.sh:95` is the build
review's fix text verbatim, and the comment above it says "scipy's and numpy's shims". It adds the
archive to the gate's input only; the link line (`:88`) is unchanged from the reviewed diff. The
restacked build's gate log is cited as "271 archives, 21964 weak names, 0 unreviewed, 0 stale"
(READ, the notes; the reviewer's own run of the gate counted 270 without it). Nothing else in the
five unreviewed commits changes a code token.

**But the method above cannot see one change, and the rebase made it (H1).** The lane found it
(its judge on `6fa6254`, `build/wave-09/lane/judge-1.log`), and I confirmed it (EXECUTED):
`tests/jobs/oracle/uv.lock` at `d5c76bb` and `6fa6254` **does not parse**. `uv tree --frozen
--offline --project tests/jobs/oracle` → "error: Failed to parse `uv.lock` / Caused by: Dependency
`numpy` has missing `source` field but has more than one matching package"; at `58f108f` and at
the reviewed `702291c` the same command parses. 100's phase 1 (`8826d72`, rebased as `4035195`)
split numpy into two `[[package]]` entries (the registry one and the `macosx_11_0_arm64` URL one)
and rewrote every dependent's `{ name = "numpy" }` into two marker lines. scikit-learn's and
seaborn's entries came to main after (044's `7d1ef9b`, 042's `163392b`), outside 100's hunks, so
the rebase applied 100's hunks cleanly and left their bare `{ name = "numpy" }` (lines 608 and
730 at the tip). The interdiff is empty because the broken lines are main's context, not either
diff's hunks: a generated file merged as text, with no hunk named and no parse after. Its effects:
`test_goldens_reproduce_under_the_pinned_oracle` is blocked ("needs oracle"), counted "unrun
locally", in the lane's run; `uv export --frozen` of the oracle project fails too (EXECUTED), so
`tests/jobs/oracle/sklearn_native_tests.sh` (044's native subset) cannot run either. The fix is a
regenerated lock (`uv lock` on 100's branch), read in section 1a.

### 1a. H1's fix, `8e7eac9` on `spec/100-numpy-on-openblas` (EXECUTED)

`git diff --stat d5c76bb 8e7eac9`: `tests/jobs/oracle/uv.lock` 4 added, 2 removed, and 100's
specification (a landing-notes bullet naming the missed merge). The lock's two hunks are exactly
the two bare lines: scikit-learn's and seaborn's `{ name = "numpy" }` each become the two marker
lines, byte for byte the form contourpy's, matplotlib's and pandas' entries already carry. No
version, hash, package or `pyproject.toml` line moves. In the scratch clone at `8e7eac9`: `uv tree
--frozen --offline --project tests/jobs/oracle` parses; `uv export --frozen` gives numpy twice,
`numpy==2.5.2 ; platform_machine != 'arm64' or sys_platform != 'darwin'` with the registry hashes
and `numpy @ …macosx_11_0_arm64.whl` with `sha256:50a68f4b…`; `uv lock --check --project
tests/jobs/oracle` → "Resolved 52 packages", no change asked for. READ, the builder's: the oracle
synced online, its numpy naming `scipy-openblas 0.3.34.0.0`, and
`test_goldens_reproduce_under_the_pinned_oracle` passing by node id (`build/100/oracle-sync.txt`,
`goldens-node.txt` in 100's worktree). The fix is what H1 asks: only the dependents' numpy lines
move.

**097 rebased onto `8e7eac9` as `a68efbb`** (EXECUTED): `git range-diff d5c76bb..6fa6254
8e7eac9..a68efbb` maps all nine commits `=` and adds `a68efbb` (its Rebase bullet); per file, the
interdiff against `d5c76bb..6fa6254` is empty but for those 3 lines of 097's specification. At
`a68efbb` in the clone: `ruff check` and `ruff format --check` green; the citation rule, the
patches rule, the specification-shape and landed-review rules and 097's root check by node id, 5
passed; the oracle lock parses.

### 097 (`dbecd2d..d914716`, its build review's range) against `d5c76bb..6fa6254`

`git range-diff`: all seven reviewed commits are `=` (identical patches), then `aa7d88c` (the build
review, copied) and `6fa6254` (the Rebase bullet). Per file: every file outside `context/` has an
empty interdiff, `CHANGELOG.md` included; `context/specifications/097-host-litter-outside-home.md`
differs by 8 lines (the wave's Rebase bullet). Clean: identical.

## 2. Conflicts between the entries and with main (EXECUTED)

- None was reported; none exists. The two entries share one file, `CHANGELOG.md`, in different
  bullets. `git merge-tree --write-tree --merge-base d5c76bb 58f108f 6fa6254` (097 applied to main
  without 100) and `git merge-tree --write-tree --merge-base dbecd2d d5c76bb d914716` (100 and 097
  each on their own base) both give a tree and no conflict.
- With main: the lane's three fixes after `dbecd2d` touch `src/wasi_python/_artifacts.py`,
  `tests/checks/test_v1_4_embedding.py`, `tests/harness/scoreboard.py` and two unit files. 097 also
  adds a check to `test_v1_4_embedding.py`, 3,900 lines below the fork child; both are at the tip
  (`test_a_forked_child_is_refused` at line 1469 with `727bd4c`'s labelled print,
  `test_the_judges_writable_roots_are_outside_the_home_folder` at 5407). No conflict marker in any
  file at the tip.
- No check of either side dropped: `tests/checks` collects 8 more nodes at the tip than on main and
  none fewer (100's seven, 097's one); `tests/unit` 1,986 → 1,996 (100's ten) → 2,003 (097's seven:
  `test_the_git_excludes_keep_out_exactly_the_litter`, three in `test_host_litter.py`, three
  OpenBLAS-script rows in `test_scipy_build.py`).

## 3. The judge: the prediction for the lane's acceptance on `6fa6254`

(Written before the lane's acceptance and before the dry run finished.)

Against `accepted.json` at `58f108f` (777/864 pass, 85 gap, 2 blocked, the chain's line 90):

| | predicted |
|---|---|
| rows | **872** (+8) |
| pass | **785** (+8: 100's seven, 097's one) |
| gap | 85 |
| blocked | 2 (the wheel, three systems), or 3 if the oracle is not synced (M2) |
| fail | **0** |
| unit suite | 2,003 rows (+17: 100's 10, 097's 7) |
| lost | **0**; absent 0; fewer 0 |
| gained | **8**: the claim blocks' seven `new` rows and 097's root check |
| judge changed | 15 files: 100's `scan.py`, `test_v1_3_data_stack.py`, `test_v1_5_rebuild_from_pins.py`, `test_scan.py`, the oracle's `pyproject.toml` and `uv.lock`; 097's `conftest.py`, `test_v1_4_embedding.py`, `guest.py`, `litter.py`, `paths.py`, `plugin.py`, `test_build_scripts.py`, `test_host_litter.py`, `test_scipy_build.py` (EXECUTED: the tip's hashes against `accepted.json`'s `judge.files`) |

**Grew.** From 100's macOS shard records (run 39535794638, the same binaries the lane will
build) against `accepted.json` at `58f108f`, by the ratchet's rule (EXECUTED, `predict.py`):
**101 rows grew**, exactly the run's own GREW count (own-guest 89, own-embedding 11,
upstream-macos 1):
- bytes, 1: `test_stdlib_zip_is_bytecode_only_and_deflated` 49,771,987 → 49,772,117 (+130);
- fuel, 100: `test_a_singular_matrix_raises_linalgerror` +1.983% snapshot and +1.408% plain (the
  two past 1%), `numpy_csv` +0.306%, `test_stdlib_c_modules_are_builtin[snapshot]` +0.278%,
  `test_no_cpython_test_module_is_built_in` +0.227%, `modelling` +0.223%, `plot_line` +0.222% /
  +0.200%, `plot_contour` +0.160% / +0.140%, `test_dup_is_refused_as_not_supported[snapshot]`
  +0.153%, … `numpy-lib` +0.018%; median +0.027%.
- Each of the 101, and each of the 55 rows that fell past the tolerance (sameness compares both
  ways), is inside 100's claim block's `grows` (EXECUTED: the claim block's entries matched with
  sameness's own `_names` rule: 0 unclaimed of 101, 0 of 55).
- **Fell, not red:** `test_binary_is_a_core_wasm_module[plain]` 93,793,595 → 92,553,279
  (−1,240,316), `[snapshot]` 98,682,976 → 97,445,041 (−1,237,935), `cpython-fs` −0.012%, 52 other
  fuel rows down to −0.192%.
- 097 grows nothing: its run 39532775277 has no GREW line with the guest folders moved, and its
  criterion 3 found every fuel row location-free.
- **And the rows CI does not measure on darwin (M1).** `accepted.json` holds darwin fuel for 56
  upstream groups; CI's macOS shard runs only `cpython-fs` and `numpy-lib`, so 100's claim lists
  only those two. The lane's local judge runs all 56. 100's effect on the other 54, measured on
  Linux (run 39535794638 against 39530569266, EXECUTED, `delta.py`): 14 up past 0.01%
  (`numpy-others` +0.255%, `matplotlib-render-1` +0.126%, `pandas-reshape` +0.103%,
  `matplotlib-render-3` +0.084%, `mpl-axes_grid1` +0.050%, `matplotlib-rest-b1` +0.042%,
  `pandas-frame` +0.040%, …), 15 down (`contourpy-config-2` −0.131%, `pandas-tslibs` −0.120%,
  `numpy-core` −0.095%, …), 27 within; every group's status and passes the same. Linux is a poor
  guide to darwin's magnitudes (wave 08's lesson), so the prediction is: **some 10 to 20 more
  darwin upstream rows grow** and a like number fall, none with a changed pass count, each
  unclaimed by row.
- So the predicted line: `lost 0 · gained 8 · grew about 101 + the upstream groups of M1`. (The
  lane's first judge then showed 116: 101 + 15; section 3a.)

**The wheel.** 100's built wheel is 90,864,009 bytes (EXECUTED: run 39535794638's
`rebuild-wheel-ubuntu-24.04`), about 0.76 MB below the base's (the same artifact's zip,
91,470,969 → 90,710,003). 097 changes no artifact byte. With 045's about 7.4 MB the wheel would be
about 98.3 MB, 1.7 MB under question 64's 100 MB line, so the landing after 045 that adds bytes is
the one the agent must bring question 64 back for (Note 6).

**The set to expect.** `python.wasm` `11d7799d…` (92,553,279), the snapshot `e65dfa2d…`
(97,445,041), the zip `02d3a3b7…` (49,772,117): 100's set `f43586b0`, since 097 changes no
artifact byte (its criterion 4). `MANIFEST` against main's `83789790` set: 100's three recipe lines
added and six changed, and 097's two (`scripts/litter.py`, `scripts/make_openblas_void_patch.sh`);
so `SHA256SUMS` is neither `f43586b0` nor `c1cc11ba` but a third value.

### 3a. The lane's first judge on `6fa6254`, against the prediction (EXECUTED)

The lane's record `build/wave-09/lane/judge-1.json` (`-n 3`, no `--accept`): `784/872 pass · 85
gap · 3 blocked · 0 fail (unit suite 2008/2010, 2 skipped)`; `ratchet vs 7a221035bf: lost 0 ·
absent 0 · unrun 0 · unrun locally 1 · gained 8 · grew 116`. Against the prediction:
- rows 872, gap 85, fail 0, lost 0, gained 8 (the eight named): as predicted.
- pass 784, blocked 3, unrun locally 1: the oracle check, blocked by H1's lock, not by the
  unsynced venv of M2; one fewer pass than predicted for that reason only.
- **grew 116 = 101 + 15.** `predict.py` over the lane's record against `accepted.json` gives the
  same 116; all 101 rows predicted from 100's CI records are among them (row for row, the zip's
  +130 bytes included), and the other 15 are darwin upstream groups, as M1 predicted ("some 10 to
  20"): `matplotlib-render-3` +0.103%, `numpy-others` +0.102%, `matplotlib-rest-a` +0.060%,
  `pandas-groupby` +0.058%, `contourpy-1` +0.056%, `pandas-io-parser` +0.046%, `mpl-axisartist`
  +0.035%, `pandas-frame` +0.033%, `matplotlib-rest-b1` +0.031%, `contourpy-filled-1` +0.025%,
  `matplotlib-render-2b` +0.020%, `matplotlib-render-2a` +0.019%, `numpy-core` +0.016%, `regex`
  +0.015%, `cpython-archives` +0.014%. All under +0.11%, far inside M1's ±0.5% bound; 71 rows fell.
  `regex` and `cpython-archives` import no numpy: the layout reason (100's L2), and
  `cpython-archives` is the row whose darwin fuel has drifted before (wave 08).
- **Sameness with the claims** (EXECUTED: `uv run python tests/harness/sameness.py --claims
  <claim file> build/wave-structural/accepted-record.json build/wave-09/lane/judge-1.json`, the
  claim file 100's block with M1's `test_upstream_suite[*` entry and L1's 097 block, saved at
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/claims/wave-09.toml`):
  `note: explained by claims: 097 2 · 100 196`, and two lines left, both the oracle check
  (`status 'pass' != 'blocked'`, `need None != 'oracle'`). The unit tally moved by exactly 17 (100's
  10, 097's 7). Without M1's entry the 15 upstream rows and their falling kin would be unexplained.
  The oracle row is not "a check blocked in that worktree": it is blocked by the entry's own lock
  (H1), so it is not clean until the regenerated lock makes it pass.

## 4. The dry runs (EXECUTED)

**The run of record, 39559520924 on `a68efbb`.** `gh run view --json jobs`: 36 jobs succeeded,
among them "build and judge (arm64 macOS)", both "rebuild from the pins" jobs, the three
"verify" jobs and "the same bytes from every host"; three failed, all macOS judge shards
(`own-guest`, `own-embedding`, `upstream-macos`); the gather and the three publishing jobs were
skipped (a red shard skips the gather). Every Windows and Linux shard is green, so 105's no-fork
child and 107's digest cache hold on this tip.
- All 33 shard records downloaded (`gh run download -p 'record-*'`); every one names commit
  `a68efbb`; no check in any is `fail` or `unrun`.
- **The gather, run locally** in the clone at `a68efbb` (`tests/harness/gather.py --records`, with
  the build record's `WASM_SHA256` `11d7799d…` and `SET_SUMS_SHA256` `142bdd38…` and each record's
  SHA-256 as its `RECORD_*`): exit 1; `780/872 pass · 85 gap · 7 blocked · 0 fail (unit suite
  4679/4709, 30 skipped)`. Red lines: **G5 "grew" only**, on the three macOS shards (own-guest 5,
  own-embedding 5, upstream-macos 1 printed; the ratchet's full list below), and **G7** twice (the
  newest acceptance is not on the release's `python.wasm` and set, as for any wave before its
  acceptance). No G1 to G4, no G6, no G5 "lost", "absent" or "records no" line.
- **The growth, row by row** (`predict.py` over the macOS and build records against
  `accepted.json` at `58f108f`): lost 0; **grew 101** (the zip's +130 bytes and 100 fuel rows,
  median +0.027%, the two singular-matrix rows +1.983% and +1.408% the most); fell 55. All 101 and
  all 55 are inside 100's claim block (section 3), and they are the same rows with the same values,
  156 of 156, as in 39555640193 and in 100's own run 39535794638. 097 adds no G5 line.
- **The set.** CI's `python.wasm` is `11d7799d…` and its `SHA256SUMS` hashes to `142bdd38…`. The
  lane's set rebuilt in the main tree at `6fa6254` (`build/wave-09/lane/build.log`: 19 steps;
  python.wasm 92,553,279 `11d7799d…`, the snapshot 97,445,041 `e65dfa2d…`, the zip 49,772,117
  `02d3a3b7…`) has `SHA256SUMS` `142bdd38…` too (EXECUTED, `shasum -a 256
  build/artifacts/SHA256SUMS`): the same set, which §5.7's comparison asks for. The tip's lock fix
  touches no recipe or script, so the set at `a68efbb` is this one.

**Supporting: 39555640193 on `6fa6254`.** The same shape: 36 succeeded, the same three macOS
shards red, 33 records with no `fail` or `unrun`, the local gather at `6fa6254` `780/872 pass · 85
gap · 7 blocked · 0 fail`, red on G5 "grew" and G7 only, the same 101 grown rows. The oracle check
is blocked in CI on both runs by design (`gather.CI_NEEDS`), so neither run could see H1: only the
lane's local judge could, and did.

## 5. Constitution checks

- **§4.1 (patches):** `recipes/patches/` and `downloads/SHA256SUMS` are untouched by the wave
  (EXECUTED, `git diff --stat 58f108f 6fa6254 -- recipes/patches downloads` empty). 100 carries no
  patch: numpy's own `BLAS_SYMBOL_PREFIX` hook, a one-line recipe header, a per-file map and a
  generated shim file are recipe files, the adaptation §4.1 asks for first, and facts sheet 31
  (`context/upstream/31-numpy-lapack-subroutines-declared-int/`, row 31 of the upstream README)
  gives the header its removal path; no pull request is owed for a recipe (its Scope says why).
  097 changes the script that makes OpenBLAS's three carried patches, not the patches:
  `test_the_openblas_patches_are_what_their_script_makes` passed in 097's run on the real tarball;
  `test_carried_patches_follow_the_rules` passes at the tip (above).
- **§4.2 pins:** the oracle's new numpy wheel is pinned by URL and SHA-256 in its `uv.lock`
  (`sha256:50a68f4b…`), an oracle (native) input, not an artifact input.
- **§4.3 to §4.5:** no `src/` file, no import or export, no `tests/public_api.txt` line changes; no
  embedder name (the rules check passes).
- **The structural rule** (spec 108, `reviews/README.md` item 4a): nothing under `src/` changes, so
  no structural review is owed and neither entry's Kind carries the token; `GUEST_TMP` is a
  judge-side module constant chosen once at import.
- **"Code speaks for itself"** (spec 109): the rule's check passes at the tip; 100's 26 and 097's
  22 rewordings are comments and docstrings only (section 1).
- **Rule 4 (the judge not weakened):** `tests/known_gaps.toml`, `tests/upstream/`,
  `context/progress/`, the goldens and `tests/release_shards.toml` are untouched by the wave
  (EXECUTED, `git diff --stat` empty). The oracle's pin moves (a judge change, named in 100's
  `--accept-judge`); every golden reproduced under it at 100's phase 2 (READ).
- **§7:** nothing tripped; no `--accept`, push or artifact in git by either entry.

## Findings, most severe first

1. **H1 (High, the lane's finding, confirmed here): 100's rebase left the oracle's lock unparsable**
   (`tests/jobs/oracle/uv.lock`, lines 608 and 730 at `6fa6254`; section 1). A rebase change no
   review read and no Rebase bullet names: scikit-learn's and seaborn's bare `{ name = "numpy" }`
   beside 100's two numpy sources. **Failure scenario:** the oracle cannot be synced or exported
   anywhere (`uv tree`, `uv export` and so `uv run --frozen` all refuse it), so the goldens check
   is blocked on every system and 044's native script cannot run; the wave would land the pass of
   `test_goldens_reproduce_under_the_pinned_oracle` carried forward on a lock that cannot install.
   100 cannot land at `d5c76bb`. **Fix (100's builder): done in `8e7eac9`**, read in section 1a:
   only the two dependents' numpy lines move, the lock parses and `uv lock --check` asks no
   change, and 100's notes name the missed merge; 097 is rebased onto it (`a68efbb`, no hunk).
   What remains: the lane judges `a68efbb` with the oracle synced (M2), and the check passes. **And for every later rebase:** a generated lock is re-parsed after a rebase
   (`uv lock --check` or `uv tree --frozen --offline` on each lock the branch touches), since a
   textual interdiff cannot see a broken line that is base context.
2. **M1 (Medium): 100's claims do not cover the darwin upstream groups the lane's judge
   ratchets.** (100's *For the lane*, the claim block's `grows` and `--accept-growth`.) The claim
   list was measured "darwin fuel only, as the ratchet keys it" from CI, whose macOS shard runs two
   upstream groups; `accepted.json` holds darwin fuel for 56, which only the lane's local `-n 3`
   run measures. On Linux 100 moves 29 of the other 54 past 0.01% (section 3); the lane's first
   judge on `6fa6254` confirmed it: 15 darwin upstream rows grew, each under +0.11% (section 3a).
   **Failure
   scenario:** the acceptance shows GREW on rows no entry names, `--accept-growth` does not name
   them, and sameness with the entries' claim blocks prints them as unexplained, which rule 6a reads
   as an ejection of 100, for a move that is 100's own mechanism. **Fix (before the acceptance,
   context only):** add `"tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*"` to
   100's claim block's `grows` in the lane's claim file (sameness's `*` prefix rule), and one
   clause to 100's `--accept-growth`: `; on darwin the upstream groups that run numpy (numpy's,
   pandas', matplotlib's, contourpy's and the rest) move by numpy's dot, products and linear
   algebra on OpenBLAS and the rebuilt binary's layout, every pass count unchanged (the integration
   review's M1; on darwin 15 groups up to +0.11 percent, the rest within or down)`. Then read the acceptance's
   upstream rows against it: any group whose **passes** move, or whose fuel moves past about
   ±0.5%, is a finding against 100, not covered by this clause.
3. **M2 (Medium): once H1 is fixed, the oracle's new numpy pin is still "unrun locally" unless the
   lane syncs it online first.** (100's Decision 7; `tests/jobs/oracle/uv.lock`.) `jobs.oracle_command` runs
   `uv run --frozen --offline` against `build/oracle/`. The main tree's oracle cache and venv hold
   only numpy's `cp315-cp315-macosx_14_0_arm64` wheel (the Accelerate one) and a cp314 one; no
   `macosx_11_0_arm64` wheel (EXECUTED: the `WHEEL` tags under `build/oracle/cache/archive-v0` and
   `build/oracle/venv`). The release blocks the oracle everywhere (`gather.CI_NEEDS`). **Failure
   scenario:** `test_goldens_reproduce_under_the_pinned_oracle` is blocked, counted "unrun
   locally", not red; the wave lands with the goldens never re-checked under the pin it changes,
   on any system. **Fix (the lane):** sync the oracle once with network before the judge, as wave
   08's M1 and the chain's addendum did (`UV_CACHE_DIR=build/oracle/cache`,
   `UV_PROJECT_ENVIRONMENT=build/oracle/venv`, its Python, `uv sync --frozen --project
   tests/jobs/oracle`; the wheel is hash-pinned), check `numpy.show_config()` names
   `scipy-openblas`, and let the acceptance run the check. It must pass.
4. **L1 (Low): 097 has no claim block and does not state its unit count.** (097's *For the lane*.)
   Sameness's `--claims` needs `units` to match the unit suite's tally exactly. Fix text, for the
   lane's claim file:
   ```toml
   [[claim]]
   spec = "097"
   new = ["tests/checks/test_v1_4_embedding.py::test_the_judges_writable_roots_are_outside_the_home_folder"]
   units = 7
   ```
   (EXECUTED: `--collect-only` of `tests/unit`, 1,996 at `d5c76bb`, 2,003 at `6fa6254`, the seven
   named in section 2.)
5. **L2 (Low): the 0.1.0a8 notes keep two sentences 100 makes untrue.** (`CHANGELOG.md`, one
   unreleased section, which becomes 0.1.0's release notes.) 037's bullet says "numpy's own LAPACK
   (`lapack_lite`) now carries a symbol prefix so it cannot meet OpenBLAS's; numpy computes as
   before" (lines 153 and 154), and 099's says the signals "raise `LinAlgError` whenever numpy's bundled
   LAPACK (`lapack_lite`) finds the matrix singular" (line 76). 100's bullet, above both, says
   `lapack_lite` is gone. Decision 11 removed 099's B1 sentences only. Fix text: in 037's bullet,
   after "numpy computes as before." add " (Later in this release numpy links the same OpenBLAS and
   `lapack_lite` leaves the binary: spec 100, above.)"; in 099's, "numpy's bundled LAPACK
   (`lapack_lite`)" → "numpy's LAPACK (`lapack_lite` then; OpenBLAS since spec 100, above)". Not
   `context/`, so it is the lane's or a builder's edit, read at the landing.
6. **L3 (Low): the judge still names 097 for work 097 does not do.** `tests/upstream/matplotlib.toml`
   line 261, the `stage-layout` expectation's reason, ends "(spec 097, reserved)". 097's Scope says
   "nothing in the judge names 097" (it read the closers, which point at `context/roadmap.md`, not
   the reasons). Once 097 lands as the host-litter specification, that reason cites the wrong one.
   Fix: none now (an allowance file's text is a judge change of its own); the specification that
   gets the lane's number for the two staging items rewrites the reason to that number. The lane's
   roadmap line should say so.
7. **Note: the wheel and question 64.** About 90.9 MB after this wave (section 3); 045's ~7.4 MB
   takes it to about 98.3 MB. The landing after 045 that adds bytes crosses 100 MB, and the agent
   brings question 64 back then, not now.
8. **Note: 100's judge-change list names `scripts/wasi-cc`.** Its *For the lane* says the judge
   hash changes in "`scripts/wasi-cc`'s comment"; `wasi-cc` is not a judge file (`accepted.json`'s
   `judge.files`), so the acceptance's "judge changed" lists the 15 files of section 3 without it.
   It moves a `MANIFEST` recipe line instead, as 100's notes also say. No action.
9. **Note: 097 carries two versions of its flags.** *For the lane* (before the landing notes) begins
   its reasons "spec 097:", the landing notes' *For the lane* "097:". The landing notes' are the
   ones its self-check names; the lane should use those.
10. **Note: the lane's acceptance duties the entries name.** Rebuild the set first (097: or
   `test_manifest_recipes_match_the_tree` is red); read 097's criterion 7 after the full judge
   (`ls` of `T/judge-wasi_python-<key>`; `find build/harness T/judge-wasi_python-<key> -type d !
   -perm -u+w`, expecting nothing); give 097's two staging items the next free number and turn the
   roadmap's 097 and 100 lines into landed lines; the disk check names `GUEST_TMP` too (21 GiB free
   on the main tree's volume at 02:30, `df`).

## Disposition (for the lane; the entries' builders where named)

1. H1 — fixed by 100's builder in `8e7eac9`, read here (section 1a); 097 rebased onto it as
   `a68efbb` with no hunk (read here). Closed once the acceptance runs the oracle check and it
   passes (with M2).
2. M1 — the lane's claim file and `--accept-growth`, before the acceptance. A claim file with the
   entry, parsed by `sameness.load_claims` and run against the lane's first judge, is at
   `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/claims/wave-09.toml`.
3. M2 — the lane: the oracle synced online in the main tree before `--accept`.
4. L1 — the lane's claim file (the block in the finding, in the same file).
5. L2 — a `CHANGELOG.md` edit by the lane or 100's builder, read at the landing; or answered in
   writing if the lane keeps each bullet as its specification wrote it.
6. L3 — the lane's roadmap line for the two staging items names the reason to rewrite.
7. Notes 7 to 10 — no action beyond what they say.

## Verdict

**Lands as merged at `a68efbb` once** the lane's acceptance there (1) runs
`test_goldens_reproduce_under_the_pinned_oracle` and it passes, the oracle synced online on the
fixed lock (H1, M2); (2) shows lost 0, gained 8, fail 0, and grows only the rows this review
names: the 101 the dry run and 100's claim block share and the darwin upstream groups of M1 (15
in the lane's first judge, each under +0.11%, no pass count moved), with M1's clause in 100's
`--accept-growth`; and (3) prints, from `sameness.py --claims` with M1's entry and L1's 097 block,
nothing but the claims' note. Both rebases are their reviewed diffs plus named conflicts, the
citation rewordings, L6's verbatim fix and H1's two-line lock fix; the entries do not conflict;
the dry run of record 39559520924 is red on growth lines 100 claims and G7 only, every Windows
and Linux shard green, and its set is the lane's (`SHA256SUMS` `142bdd38…`). No entry to eject:
H1 was 100's and is fixed on the tip; were the oracle check still to fail after the sync, 100
would be ejected and 097 land alone (097 touches nothing of 100's).

One line: numpy on OpenBLAS and the guest folders outside the home folder merge cleanly; the one
real defect, a rebase that broke the oracle's lock, is fixed on the tip; the rest is claims the lane
must widen to the darwin upstream rows CI never measures.
