# Review of 097 — host litter outside the home folder (the build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of 097 and reviewed none of it before; the pre-build review was another agent's.
- **Reviewed:** `dbecd2d..d914716` on `spec/097-host-litter-outside-home` (code tip `90eed13`; `90eed13..d914716` touches only `context/`, READ by `git diff --name-only`).
- **Box:** 60 minutes (build-class, the lane's box); finished inside it.
- **Run:** no run of my own. The builder's run **39532775277** is on `90eed13`, the exact code commit, so I read it back (AGENTS.md rule 8, the owner, 2026-10-20): `gh run view 39532775277 --json jobs`, every record downloaded with `gh run download`, and the gather re-run locally.
- **Re-ran (EXECUTED, darwin-arm64):**
  - `tests/harness/gather.py` over the 33 shard records of run 39532775277, with the build's `WASM_SHA256` (`ee45b241…`) and `SET_SUMS_SHA256` (`c1cc11ba…`) and each record's SHA-256 → exit 1. Red lines: G4 and G5 for `windows/own-embedding test_a_forked_child_is_refused`, G7, and 33 G2 "commit 90eed13c7390 is not HEAD" (mine alone: I gathered at `d914716`, which is `90eed13` plus `context/`). **No `G5 … grew` line, no other lost row.** 772/865 pass, 85 gap, 7 blocked, 1 fail; unit suite 4643/4673, 30 skipped. This is the builder's `ci-39532775277-gather.txt`, line for line.
  - The base's run 39530569266 on `dbecd2d`: the same one job red, `judge (windows-2025, own-embedding)`, the same check, the same diff (`'True False'` against `"{'used': True, 'forked': False}"`). That shard: 176 passed there, 177 here (the new root check).
  - Both runs' `release-assets` tarballs, unpacked side by side: `diff -rq` names only `MANIFEST` and `SHA256SUMS`. `MANIFEST` differs in lines 269 and 270, the `recipe` lines of `scripts/litter.py` and `scripts/make_openblas_void_patch.sh`; their new hashes are `git show 90eed13:<file> | shasum -a 256`, the old ones `dbecd2d`'s. `SHA256SUMS` differs in its `MANIFEST` line only: `83789790` (base) against `c1cc11ba` (build).
  - By node id, in the worktree (`build/097-review/probes.txt`): the four OpenBLAS script rows (the three new ones and spec 090's), `test_the_git_excludes_keep_out_exactly_the_litter`, all of `tests/unit/test_host_litter.py`, and `test_the_judges_writable_roots_are_outside_the_home_folder` → 29 passed, ratchet lost 0, grew 0. Afterwards `T/judge-wasi_python-11909bf415b5` existed and was empty.
  - My own probe (scratchpad, Apple Git 2.50.1, `core.ignorecase=true` on APFS): with `:(exclude,glob)**/.DS_Store` and `:(exclude,glob)**/._*`, `git add -A --force` staged `.ds_store` and `keep` and left out `._A`. git's exclude is case-sensitive, as `has_litter` is, so the excludes never drop a real file that `has_litter` would keep.
  - `git merge-tree --write-tree 727bd4c d914716` → exit 0: 097 rebases cleanly onto the base's fix commit, which edits the same check file elsewhere.
- **Not run:** the fast tier (another agent held `build/slots/fast`); no build.

## Acceptance criteria against evidence

1. **The checks fail first** — met, READ. `first-fail-root.txt`, `first-fail-script.txt`, `first-fail-unit.txt` and `first-fail-unstage-reverted.txt` hold the four lines the criterion names, on `5805af0`'s harness and script. The rebase changed only comments and docstrings (`90eed13`), so the lines still stand.
2. **They pass with the build** — met, EXECUTED: 29 passed by node id here (above); in CI the new root check passes on darwin-arm64, linux-x86_64 and win32-amd64 (each own-embedding record), and the unit suite has no failure.
3. **Fuel is location-free** — met. READ: `repeats-a-compare.txt` and `repeats-b-compare.txt` on `5805af0`: every fuel row one value across four legs, two of them main's code from a clone outside the home folder. EXECUTED here, for the rebased tip: the CI macOS records have no growth line, and `upstream-macos` measured `numpy-lib` (132,483,747,240) and `cpython-fs` (63,199,952,331) **equal to `accepted.json`'s darwin-arm64 values**, with the guest folders under the runner's temporary folder (the root check passed there). That also measures `numpy-lib`, which was blocked in every local leg.
4. **The set** — met, EXECUTED: the two CI-built sets differ in exactly the two recipe lines; `python.wasm`, the snapshot and the stdlib zip are byte for byte the same. The lane's own rebuild is still the lane's step (below).
5. **The OpenBLAS check** — met: `test_the_openblas_patches_are_what_their_script_makes` passes in the CI build record (EXECUTED, read), and in `openblas-check.txt` (READ).
6. **Nothing else moves** — met in substance, not to the letter, for two reasons the builder names. The fast tier had one red row, `test_manifest_recipes_match_the_tree`, because the copied set's `MANIFEST` was built from the base's two scripts; CI's fresh set passes that row (v1.1 46/46). The CI run is red only on the base's Windows fork row, which the base's own run shows too. Linux and Windows: `GUEST_TMP` is `HARNESS_TMP` there, the same object, so no path, root or message changes except the recovery text naming the real folder (READ).
7. **Cleanup** — partly met. After the builder's fast tier and after my probes, `GUEST_TMP` was empty. The full judge's cleanup is for the lane to read at acceptance (below).

## Findings, most severe first

No High. No Medium.

1. **Note — criterion 6 is met only once the base's fix is in.** The run is red on `test_a_forked_child_is_refused` on Windows. That row is the base's: run 39530569266 on `dbecd2d` fails it in the same way, and 097 touches no runner or fork code (READ: the diff names no `src/` file). Failure: a wave built on `dbecd2d` alone stays red on Windows. Fix: none in 097. Land it on a tip that holds `727bd4c`; it merges cleanly there (EXECUTED).

2. **Note — the new unit rows never run on Windows.** `test_host_litter.py`, `test_build_scripts.py` and `test_scipy_build.py` sit in `own-rest`, which runs on macOS and Linux only (`tests/release_shards.toml`). Their `win32` skips are therefore never run. Windows' only branch that matters, the root check's non-darwin leg, runs and passes in `own-embedding` on Windows. This is the shard plan as it was, not a gap 097 opens.

3. **Note — with `TMPDIR` unset on darwin, `GUEST_TMP` falls under `/private/tmp`.** `tempfile.gettempdir()` falls back to `/tmp` (for example under `env -i`). The spec ruled `/private/tmp` out because it is shared. The build still holds there: `_make_guest_tmp` refuses a folder that another user made, or one with group or other bits, by name (READ, and the unit row). `host_roots_always` adds `GUEST_TMP` when the temporary folder is `/tmp`. At worst another user blocks the run; it is never measured wrong. No change needed.

4. **Note — the user-facing messages still say "spec 097".** Two assertion texts in the new check and `_make_guest_tmp`'s refusal cite the specification in string literals. Spec 109's rule covers comments and docstrings only, and `litter.remove` already ends "(spec 089)", so the rule holds. Rewording them is the next rule-change's business, not this one's.

## Rule 4: the judge is not weakened

- No existing check, golden, gap, allowance, upstream plan or progress file is edited (`git diff --stat dbecd2d..90eed13 -- tests/known_gaps.toml tests/upstream context/progress` is empty). In the test files there are additions only. The one changed fixture, `guest_workdir`, is claimed.
- The seal and the watch are as before. `host_roots_always` gains a root, so it is stricter.
- No check depends on a guest root being inside the checkout. `grep` for `REPO`, `HARNESS_TMP` and `workdir` paths in `not in` or `is_relative_to` assertions finds only the new check.
- Every run root comes from `guest_workdir`: `upstream.Session`, `packages.Session` and `regrtest.Session` all take it (READ, `test_v1_3_upstream_suites.py`). The package stages `upstream-<package>` (066's, landed since the draft) are sealed (`litter.seal(root)`) and stay under `build/harness`, as the principle says.

## Structure (checklist item 4a)

There is no `src/` change. The one platform branch is the judge's (`paths.GUEST_TMP`, chosen once at import). `GUEST_TMP` is a module-level constant, not mutable. Not structural, and the Kind line is right.

## Self-check

Every item is ticked and true as I read it. The CI run is on the exact code commit; the Windows red row is named as the base's; the growth list is empty; the claim list matches the diff (one check gained, unit rows, nine judge files).

## For the lane, at acceptance

- **Rebuild the set first.** Otherwise `test_manifest_recipes_match_the_tree` is red, as in the builder's fast tier. Expect `MANIFEST` to differ from the base's set in the two recipe lines only. Expect `python.wasm` `ee45b241…`, the snapshot `9c2af970…` and the zip `fb12a1e6…`. On a base of `dbecd2d` plus `727bd4c`, which touches no recipe, expect `SHA256SUMS` `c1cc11ba…`.
- **Read criterion 7 after the full judge.** Run `ls` on `T/judge-wasi_python-<key>` (the key is from the tree the lane judges in). Expect no `guest-*` folder left. Then `find build/harness T/judge-wasi_python-<key> -type d ! -perm -u+w`; expect it to find nothing. Record both lines in the landing notes.
- **The disk.** The main tree's volume had 27 GiB free at 23:26 (`df`, 99% used). `GUEST_TMP` is on that volume, so the lane's disk check names it too (pre-build note N8).
- **The record to expect:** gained `test_the_judges_writable_roots_are_outside_the_home_folder`; lost 0; grew 0; `judge changed`. Use the landing notes' flags as written. No `--accept-growth`.
- **The Windows fork row** must be green on the wave's tip, from `727bd4c`, not from 097.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Note 1 — for the lane; no change.
2. Note 2 — no change.
3. Note 3 — no change.
4. Note 4 — no change.

## Verdict

Lands: every criterion is met with evidence, except criterion 7's full-judge reading and the rebuilt set, which are the lane's at acceptance, and the base's Windows row, which `727bd4c` fixes.

One line: 097 moves the unsealed guest folders out of the home folder on macOS without moving a fuel value or a byte of the three artifacts, and the OpenBLAS script no longer races the writer.
