# Delta review of 043 — matplotlib, the second milestone: triangles, contours, SVG and PDF

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of 043. I did not write its spec review or its build review.
- **Reviewed:** the build review's range `08de0c8..737cef6` (kept as local branch `backup/043-pre-rebase-737cef6`), against the rebased branch. I checked it in two steps: `ebd0449..6e127e8` (on main after wave 04), and then `41bcc0f..047508c` (the builder's rebase onto wave 05, pushed while I was reviewing).
- **Time box:** 40 minutes (build-class delta). I used about 35.
- **Run:** none of my own. The coordinator asked me to read the branch dry run `39369636353` on `c448232` and not to rebuild. No run exists on `047508c` (L2).
- **Re-ran** (in the `wasi_python-043` worktree at `047508c`; `build/lane.lock` was absent each time; logs in `build/043-delta/`):
  - `uv run pytest -n 3` on `tests/unit/test_build_scripts.py`, `test_artifact_rules.py`, `test_runner_mounts.py`, `test_scan.py` and `test_patches.py`: 384 passed, exit 0.
  - `tests/checks/test_rules.py -m "not slow"`: 43 passed, 1 skipped, exit 0. I ran it before and after my write-in.
  - `tests/checks/test_v1_5_rebuild_from_pins.py -k test_source_tree_matches_its_tarball`: `23 passed, 19 deselected in`. This is the exact line the release workflow's grep expects.
  - `ruff check` and `ruff format --check` on `src`, `tests` and `scripts/meson_plan.py`: green.
  - `gh run view 39369636353 --json jobs` and `--log-failed`.
  - My script `043-delta/cmp2.py` compares the dry run's three macOS shard records and the fast tier's record (`043/ci-records/`, `043/fast-086-latest.json`) with 086's accepted record.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## The range-diff

- **Old range against `ebd0449..6e127e8`** (EXECUTED, `git range-diff`):
  - Commits 3 and 4 (landing notes; `737cef6`'s answers to F1, F4, F5 and F6) are `=`.
  - Commits 1 and 2 changed only where the conflicts were named.
  - Commits 5 to 8 are new and touch `context/`, README and CHANGELOG only.
- **Every non-context file compared** (EXECUTED): for each file the branch changes, I compared its added and removed lines in the old range with those in the new range.
  - All are identical except `.github/workflows/release.yml` (the tree count) and `tests/checks/test_v1_3_data_stack.py` (`DISTRIBUTIONS`).
  - So `70_zip.sh`, `60_link.sh`, `known_gaps.toml`, `make_stdlib_zip.py`, `assemble_artifacts.py`, the patch and the harness bring exactly the lines the build review read.
- **`6e127e8` against `047508c`** (EXECUTED): commits 1 and 3 to 8 are `=`. Commit 2 differs in one context line only: 090's `SKIP_NAMES` (litter by `is_litter`) sits next to 043's `REWRITE`, which is unchanged. Commit 9 changes `context/` only.
  - The same line-by-line check over all 33 non-context files of `41bcc0f..047508c` gives no difference from `ebd0449..6e127e8`.

## The named conflict hunks

1. **The hostile-guest file.** No test was dropped (EXECUTED: sorted `def test_` lists).
   - Old base 44 → old tip 45. `ebd0449` 57 → `6e127e8` 58. `41bcc0f` 57 → `047508c` 58.
   - Each time the only difference is `test_a_triangulation_leaves_every_writable_grant_as_it_was`.
   - Its added lines are byte for byte the old range's.
   - 078's and 086's checks (`test_dup_is_refused_as_not_supported`, `test_the_string_hash_is_siphash13`) come first, as the notes say.
2. **Step 70's guard.** 086's `MISSING_INFO` lines come first, then the loop `pillow kiwisolver matplotlib contourpy`. The `--tree` and `--metadata` lines for contourpy sit beside 039's and 041's (READ).
3. **`DISTRIBUTIONS`.** `contourpy` is in sorted place among tier A's names. The comment names specs 023, 046, 039 and 043. 45 entries (READ).
4. **`known_gaps.toml`.** Exactly the two M1 gaps and their comment are removed: 67 → 65 entries at `41bcc0f..047508c`. 065's and 086's entries stay (EXECUTED).
5. **README rows.**
   - Patch row: 11, with "matplotlib's enum fix".
   - The "eleven carried patches" sentence, and *How it is built* naming all eleven.
   - The zip row with contourpy.
   - The sizes row 42.3 / 46.5 / 38.8 MB (F3, from 42,251,129 / 46,533,054 / 38,788,145).
   - *Since then* and *Out* as described (READ).
6. **Patch count 11** (EXECUTED): `recipes/patches/*/*.patch` has 11 files. `test_carried_patches_follow_the_rules` passes.
7. **Release tree count 23** (EXECUTED): `needs.SOURCE_COMPONENTS` has 22 on `41bcc0f` and 23 on the branch. The zero-patch selection prints `23 passed, 19 deselected in`. The build review's "22" predated 041's networkx sdist, so the builder is right to say 23.
8. **`make_stdlib_zip.py` (the rebase onto 41bcc0f).**
   - 090's `walk` now drops a litter name, with `is_litter`: an OS name or an AppleDouble `._` prefix (READ, `scripts/litter.py`).
   - No file in contourpy's tree has such a name, and `meson_plan.py` copies only the file meson's plan names.
   - So a rebuild should differ from `4c7099a4` in `MANIFEST`'s recipe lines and `SHA256SUMS`'s `MANIFEST` line only (INFERRED; wave 05's own rebuild found the same for 090 alone).
   - The lane's rebuild in the main tree confirms it.

## Do 737cef6's answers close F1, F4, F5 and F6?

- **F1: closed.** Criterion 5 and "Where the other growth comes from" give the build review's measured causes (READ).
  - The plain start's growth is the zip's.
  - The snapshot start's growth, the snapshot probes' and numpy-core's are the binary's.
  - No directory is re-read.
  - The new flag says the same against 086's set. The snapshot start's +122,018 there is labelled INFERRED to be the same static-data move, which is honest.
- **F4: closed.** Roadmap line 127 names "contourpy (spec 043)" in 066's reserved line (READ).
- **F5: closed.** `scripts/meson_plan.py` reads `intro-install_plan.json`.
  - It takes every entry with `tag: None`.
  - It refuses a destination outside `{py_platlib}`/`{py_purelib}`.
  - It stops unless the destinations are exactly the expected list.
  - It copies each file to its planned place.
  - Step 55 calls it with `$(dirname "$SITE")`, the site-packages folder (READ).
  - `test_untagged_files_go_where_meson_s_plan_says` and `test_a_moved_or_stray_untagged_file_stops` pass (EXECUTED).
  - The rebuild after it gave one `SHA256SUMS` on three hosts. So the placed bytes are the ones the build review saw (READ, the notes and the same-bytes job).
- **F6: closed.** `test_contourpys_notice_holds_gists_and_qhulls_its_copying` passes (EXECUTED). It covers three cases: the notice missing from contourpy's file; qhull judged by content; a matplotlib tarball without `LICENSE_YORICK`. The notes say it was seen failing first, with each rule emptied (READ).
- **F2 and F3** (at the rebase): the entry is under `## 0.1.0a8 — unreleased`, and the sizes row is restated (READ).

## The claim list and flags against the evidence

- **5 new checks: met** (EXECUTED, `cmp2.py`). Five ids are absent from 086's record and pass:
  - in the dry run's own-guest shard: `test_plot_contour_job_matches_native[plain]` (fuel 11,323,411,159), `[snapshot]` (10,996,023,540), `test_contourpy_runs_one_thread` (1,003,783,457) and the triangulation check;
  - in the fast tier: `test_source_tree_matches_its_tarball[contourpy]`.
- **Two gaps now passing: met.** `test_contour_runs` and `test_delaunay_triangulation_runs` are `gap` in 086's record and `pass` in own-guest (EXECUTED).
  - Own-guest's "gained 7" is these six plus `test_wheel_carries_the_artifact_set`. That check runs only on CI and is blocked on the lane's machine, so it is not 043's.
- **Fuel figures: met exactly** (EXECUTED). Over the three macOS shards against 086's darwin metrics:
  - 186 fuel rows move, 151 up and 35 down.
  - The median is +0.075%, the range −0.101% to +0.452%.
  - The top rows are the zip-directory and dotted-builtin checks, as claimed.
  - `test_guest_runs_here[plain]` goes 221,669,921 → 222,096,155, and `[snapshot]` 48,820,209 → 48,942,227.
- **The fast tier: met.** 585/713, 0 fail, unit 1786/1793; lost 0, gained 1, grew 123 (READ, `fast-086.log`; record commit `c448232`, artifact `1b60cc5e…`, which is `python.wasm`'s hash).
- **Byte rows: met.** The GREW lines give 41,169,347 → 42,251,129 and 45,444,036 → 46,533,054 (READ, `ci-grew.txt`).
- **Base:** wave 05's acceptance moved no metric (its landing line). So 086's record is still the right base at `41bcc0f` (READ).
- **Unit-suite wording: off by one** (L3, written in). There are six new test functions (eight items) and one renamed function, not "seven new".

## CI run 39369636353 on c448232

EXECUTED (`gh run view`, `--log-failed`):

- `headSha` is `c448232`.
- The three red jobs are `judge (macos-15, own-guest)`, `own-embedding` and `upstream-macos`. Each prints `0 fail`, `lost 0 · absent 0 · unrun 0`, and `RED: 110 / 28 / 2 metric(s) grew`.
- Green:
  - all four Windows judge legs (own-guest, own-embedding, own-runner, upstream-windows);
  - every Linux shard;
  - both Linux rebuilds and "the same bytes from every host";
  - verify on all three systems;
  - `build and judge (arm64 macOS)`, macOS own-rest and own-runner.
- The gather, publish and attest jobs were skipped.
- So 043's new checks have now passed on Windows, which the build review noted no landing had done. own-guest on Windows includes them (READ, `tests/release_shards.toml` per the build review).

## The PDF pin under SipHash-1-3: sound

- matplotlib 3.11.2's `_get_subset_prefix` hashes `frozenset(charmap.values())` (READ, `backend_pdf.py:808,818`). The Type 1 path hashes `charmap.values()`.
- `CharacterTracker.used` maps character codes to `GlyphIndexType`, which is `NewType('GlyphIndexType', int)` (READ, `_backend_pdf_ps.py`, `ft2font.pyi:18`).
- An int's hash takes no key. A frozenset's hash mixes its elements' hashes with CPython's own shuffle, not with SipHash. So neither the algorithm nor the seed reaches the tag.
- What does reach it is `Py_hash_t`'s width: 32 bits in the guest. The CHANGELOG already names this as the one difference from native.
- `PDF_SHA256` has not changed since commit 1 (EXECUTED, `git log -S`). The check passed on the rebuilt set on macOS, Linux and Windows in the dry run (EXECUTED, the records and the green legs).

## Findings, most severe first

No High. No Medium.

1. **L1 — `--accept` names a `SHA256SUMS` the landed commit will not have** (spec, the exact flags).
   - The lane rebuilds `047508c`, and 090's recipe lines change `MANIFEST`. So the set's `SHA256SUMS` will not be `4c7099a4`.
   - Fix (written in): the flag now says `4c7099a4` at `6e127e8`, then the lane's own `SHA256SUMS`, equal in every file but `MANIFEST`. The lane fills in its hash, as wave 05 did.
2. **L2 — no release-workflow run on the commit that lands.**
   - `39369636353` is on `c448232`. `047508c` adds wave 05 (090's litter rules, 082's upstream harness) and one merged recipe line.
   - The risk is small (INFERRED: one context line, no 043 line changed).
   - Fix: the lane's serial judge in the main tree covers macOS. Windows is next judged in the pre-tag dry run (rule 6b). If the lane wants Windows evidence before it accepts, it dispatches the workflow on `047508c`. No write-in needed.
3. **L3 — the unit-suite count in the claim list and `--accept-judge`.** "Seven new test functions" is six new and one renamed (`test_host_facts_in_the_three_members_are_named`).
   - Fix (written in).
4. **L4 — `--accept-growth` does not name the upstream groups that only the lane's darwin judge compares** (numpy-core, pandas, cpython-a to c).
   - The notes say so, but the flag lists only cpython-fs and numpy-lib.
   - On the old base, numpy-core grew +0.45% from the binary.
   - Fix (written in): a clause naming those groups as the binary's, with their passes unchanged. If the lane's judge shows any of them above +1%, or any pass moving, the landing stops for a stated reason.

Notes, no action:

- The CI-only `test_wheel_carries_the_artifact_set` is one of own-guest's seven gains (see above).
- The lane's ratchet compares with `c74d0f0`'s record, not 086's. Wave 05 moved no metric, so the figures stand.

## Constitution checks

- **§4.1.** Patch 0002 is unchanged through both rebases. There are 11 patches, and the zero-patch check passes on 23 trees (EXECUTED).
- **§4.12.** The notices are unchanged. The licence rule now has a unit test (F6).
- **Judge integrity** (AGENTS rule 4): no golden, allowance or progress file changed in the delta. The two gaps are removed because they pass. No check was dropped (EXECUTED).
- **§7:** nothing tripped.

## Write-in

My write-in is one commit on `spec/043-matplotlib-second-milestone` after `047508c`. It changes `context/` only: the spec's claim list, the three flags (L1, L3, L4) and a paragraph after the flags. `test_rules.py -m "not slow"` stays at 43 passed and 1 skipped.

## Verdict

**Lands.** The rebase brings exactly the reviewed lines, plus the named merges. F1, F4, F5 and F6 are closed. The claims match the records to the row. The dry run is red only for growth. The PDF pin rests on int hashing, which SipHash does not touch. L1 to L4 are Lows, written in or left to the lane.

## One line

The rebased 043 is the reviewed 043 plus clean merges; its numbers match the dry run's records; it lands, with the lane stating its own rebuilt `SHA256SUMS`.
