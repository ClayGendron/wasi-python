# Build review of 043 — matplotlib, the second milestone: triangles, contours, SVG and PDF, 2026-10-19

- **Reviewer:** a fresh agent. I wrote none of 043, neither its specification nor its build.
- **Under review:** `spec/043-matplotlib-second-milestone` at `1b6e648`, on main `08de0c8`, in
  the worktree `wasi_python-043`. It was built under the spec's **branch A** (037 has not landed).
  - Commits: `0f9e28c` (the judge), `38a882b` (the recipe, patch 0002 and its facts sheet,
    README, CHANGELOG, the release workflow's tree count 19→20), `1b6e648` (landing notes;
    EXECUTED, `git diff --stat 38a882b 1b6e648`: only the spec and one CHANGELOG line, so no
    build input moved after the cross-host builds).
  - The specification, its two Dispositions and the builder's nine amendments; the pre-build
    review `../reviews/043-matplotlib-second-milestone-spec-2026-10-17.md`.
- **How I ran it:** read only in the worktree, against its own `build/artifacts`
  (`SHA256SUMS` `697d8e46…`). My scripts and logs are in my scratch folder
  (`043-buildreview/`: `probes/`, `*.log`, `suite-*.json`). For the base I used the builder's
  copy of 023's set (`scratchpad/043/base-artifacts`, `SHA256SUMS` `c9dcb5b8…`), copied and
  checked with `shasum -c` (all OK): main's own `build/artifacts` disappeared mid-review (another
  agent is rebuilding the main tree), so I did not use it. I wrote nothing in any git tree;
  `git status` in the worktree is clean. Probe run folders are removed.

Labels: **EXECUTED** (I ran it), **READ**, **INFERRED** (reasoned, not run).

## Short version

The build does what the specification says, and the judge agrees.
- Patch 0002 is recorded as §4.1 asks. It is minimal, and it opens nothing.
- `fd_renumber` cannot be reached from Python, and the runner counts it correctly anyway.
- The licences are right. The `_build_config.py` copy is sound and host-neutral.
- My full judge (`-n 3`) gives the builder's numbers exactly: `sameness.py` finds no difference.

One finding needs fixing before acceptance, and it is about words, not code. Two growth reasons
in the landing notes (amendments 8 and 9, and the "other growth" paragraph) blame the zip's 19
new members. I measured both, and the zip does not cause either of them. The binary does. The
lane must not accept growth with a reason that has been refuted (rule 5).

**Verdict: lands once F1 is fixed in the landing notes** (and the accept-growth reason with it),
after the lane's rebase, rebuild and release dry run below.

## What I re-ran (EXECUTED)

- **Full judge**, `uv run pytest -n 3` in the worktree: `543/559 pass · 13 gap · 3 blocked · 0
  fail` (unit suite 1503/1510, 7 skipped); ratchet vs `9a446e03f6`: lost 0, absent 0, unrun 0,
  unrun locally 1 (the prior-art clone, blocked on this machine as for the builder), gained 7,
  grew 148, judge changed. Red only for growth. 2046 passed, 10 skipped, 13 xfailed in 11 min
  17 s. **My record:** `043-buildreview/reviewer-full-latest.json` (for the lane's sameness step).
- **`uv run python tests/harness/sameness.py <builder's latest-043-full.json> <mine>`:** no
  difference, exit 0.
- **Fast tier**, `uv run pytest -m "not slow" -n 3 --progress-latest <scratch>` (so the worktree
  keeps my full record): `500/559 pass · 1 gap · 3 blocked · 0 fail · 55 deselected`
  (unit suite 1503/1510); lost 0, unrun 0, unrun locally 1, gained 1, grew 126; 2003 passed,
  10 skipped, 1 xfailed in 6 min 51 s. Its record is `043-buildreview/fast-latest.json`.
- **The checks this spec adds or turns**, all pass in my record:
  `test_plot_contour_job_matches_native[plain|snapshot]` (11,217,332,358 / 10,891,553,818
  fuel), `test_contourpy_runs_one_thread`, `test_a_triangulation_leaves_every_writable_grant_as_it_was`,
  `test_delaunay_triangulation_runs` and `test_contour_runs` (gap → pass),
  `test_source_tree_matches_its_tarball[contourpy]` (20 trees), `test_stdlib_zip_names_no_build_host`,
  `test_licence_notices_cover_every_component`, `test_every_package_names_its_own_suite`,
  `test_goldens_reproduce_under_the_pinned_oracle`, `test_static_constructors_are_reviewed`,
  `test_target_features_are_the_lines[*]`, and **051's `test_callbacks_have_the_types_cpython_calls`**
  (green, as 051's Decision 4a binds).
- **The cross-host evidence** (READ, the builder's scratch `043/lin-arm` and `043/lin-x86`):
  each `host.txt` names the container (aarch64 and x86_64 Debian 13.7), `run.sh` runs
  `00_download.sh` and `build.sh --plain` on a clone at `38a882b`, and each `SHA256SUMS` is the
  worktree's byte for byte (EXECUTED, `diff`). So does the clean clone's (`clean-SHA256SUMS`,
  `697d8e46…`).

## Findings, most severe first

### F1 (Medium; blocks acceptance as worded): two growth reasons are refuted by measurement

The landing notes give two causes as INFERRED: the snapshot `-c pass` growth (+64,820, +0.41%,
amendment 8 and table row) is "about 3,400 a member", and numpy-core's +1.1 G (amendment 9) is
the suite re-reading the zip directory "at each `importlib.invalidate_caches()`, about 2,450
times". The same paragraph puts the v1.2 and v1.4 snapshot probes' +65,000 down to the zip too.
I measured each with the judge's driver (fixed clock and entropy; fuel exact), mixing the two
binaries and the two zips (EXECUTED, `probes/measure*.py`, `measure.log`):

| run | base binary, base zip | base binary, new zip | new binary, base zip | new binary, new zip |
|---|---|---|---|---|
| snapshot `-c pass` | 15,631,800 | 15,631,800 | 15,696,620 | 15,696,620 |
| plain `-c pass` | 167,481,449 | 167,919,105 | 167,473,284 | 167,929,331 |
| numpy-core, plain binary | 204,136,883,982 | 203,979,602,220 | 205,057,976,630 | — |

- **Snapshot start: the zip costs nothing.** Each snapshot gives the same fuel with either zip.
  The snapshot holds the zip's directory from snapshot time, and `-X importtime -c pass` shows
  no import during the run. The growth stays with `-S` (+63,697) and `-I` (+64,289). So the
  +64,820 is the **binary's**, not 19 members'.
- **Plain start: the builder is right.** The zip adds +437,656 (base binary) or +456,047 (new
  binary): about 23,000 to 24,000 a member, spec 035's plain-start read. The binary alone
  moves it by −8,165 or +10,226.
- **numpy-core: the zip does not grow it.** On the plain binary, the 19 members change the
  suite by **−157 M** (−0.08%), and the new binary alone adds **+921 M** (+0.45%), with the
  same 9,519 passes in every run. An instrumented snapshot run (a prelude in `drive.py` that
  wraps `zipimport._read_directory`, `importlib.invalidate_caches`, `_imp.is_builtin`,
  `PathFinder.find_distributions` and `zipimporter.get_resource_reader`) counted **no**
  directory read and **no** `invalidate_caches()` call. It counted 579 `is_builtin` calls,
  4 metadata searches and 3 resource readers. So the mechanism the notes give does not happen.
  (A snapshot binary cannot run with the other zip: with mismatched pairs the guest exits 1 or
  writes no stream. So the 2×2 for numpy-core is on the plain binary.)
- **What the binary does, as far as I could measure.** The inittab has two more entries:
  `is_builtin` costs 28,143 → 28,554 a call (+411; EXECUTED, 10,000 calls). But 579 calls
  explain about 240,000, not 1.1 G, and `-c pass` makes no call. Static data ends 108,944 bytes
  later (23,433,948 → 23,542,892; EXECUTED, the data segments), so every heap address moves.
  The same Python work then costs a little more or less: `import importlib.util` +75,053
  (+1.5%), the plain start −8,165, and the instrumented numpy-core runs differ from the
  uninstrumented ones by 0.1%. INFERRED: the moved heap changes pointer-derived hashing and
  allocation (the type method cache keys on name addresses; obmalloc's arenas sit
  differently). Two attempts did not find one call site (rule 7), so I stopped there.

**Fix, before the lane accepts:** amendments 8 and 9, the table row and the "other growth"
paragraph say what is measured. The plain start's growth is the zip's 19 members. The snapshot
start's growth, the snapshot probes' and the upstream suites' growth come from the larger
binary. It is not the zip, and not a directory re-read. The `--accept-growth` reason says the
same. No code change is needed. The amounts stay within what Decision 10 lets a build review
accept as growth: no pass is lost, and the counts are unchanged.

### F2 (Low): the CHANGELOG entry sits under a released version

The entry is under `## 0.1.0a7 — unreleased`. Main has since released 0.1.0a7 (`2737b29`) and
bumped to 0.1.0a8 (`b08def8`). At the rebase, move the entry under 0.1.0a8, as 039's rebase did
(`0dd1ddd`). READ.

### F3 (Low): the README's size row is stale

`README.md`'s facts table still says `41.1 MB / 44.6 MB / 22.2 MB` (spec 069). This set is
42.2 / 45.7 / 22.3 MB, and after 039 the zip is larger again. Update it once, on the rebased set.
No check reads that row. READ.

### F4 (Low): contourpy's suite closer is not named in the roadmap

`tests/upstream/packages.toml` gives contourpy `kind = "later"`, `closes_with = "spec 066"`.
That is what the rule allows: 066 is reserved, and the check passes. But the roadmap's reserved
line for 066 lists "matplotlib, pillow, kiwisolver, lxml and regex". The builder says 066
"should name contourpy", but the line was not changed. Add contourpy to that line when 043
lands (`context/` only). READ.

### F5 (Low): step 55 checks that meson plans `_build_config.py`, but not where

Step 55 greps `intro-install_plan.json` for the build file's path as a key, and then copies the
file to a fixed `$SITE/util/_build_config.py`. The plan also gives the destination,
`{py_platlib}/contourpy/util/_build_config.py` (EXECUTED, read from this build's plan). If a
later contourpy moved the file, the check would still pass, and the copy would put it in the
old place. Either check the destination string too, or place the file from the plan, as
`place_extensions.py` does for the archives. This is about robustness: today's bytes are right.
READ and EXECUTED.

### F6 (Low): the new borrowed-licence rule has no unit test

`paths.BORROWED_LICENCE` and `_borrowed_licence` are a new branch of the judge. They are not
among the checks the landing notes saw failing first, and no unit test covers them. I mutated a
copy of the set's `LICENSES/` (EXECUTED). With GIST's notice cut from `contourpy.txt`, the rule
names `LICENSES/contourpy.txt does not contain matplotlib's LICENSE/LICENSE_YORICK`. With
`qhull.txt` emptied, it also names `qhull-8.0.2.tar.gz`'s licence. So the rule works. A unit
case, like those for `MORE_LICENCE`, would keep it working. Not a blocker.

## The eight points asked

1. **Patch 0002 (§4.1): recorded, minimal, opens nothing.**
   - The patch file is `fix.patch` byte for byte: 1,138 bytes, SHA-256 `8ea3cd41…7da20`
     (EXECUTED). `MANIFEST` names it (`recipe 8ea3cd41… recipes/patches/matplotlib-3.11.2/0002-…`,
     line 115, EXECUTED).
   - Its facts sheet moved unchanged (`similarity index 100%`) to
     `context/upstream/patches/matplotlib-3.11.2/0002-qhull-without-devnull-on-wasi.md`. It has
     020's six header lines, with `Status: drafted`, and it is a facts sheet, as question 80
     asks, because matplotlib refuses AI-made pull requests (READ).
   - The CHANGELOG names it, and the README count is 8 (READ). 020's zero-diff check passes on
     20 trees (EXECUTED, my record).
   - It is 12 added lines, all under `#ifdef __wasi__`; every other platform keeps
     `fopen(MPL_DEVNULL)` (READ).
   - **Opens nothing** (EXECUTED, the binary's name section and its call instructions):
     `fopencookie` calls only `__ofl_add`, `malloc`, `memchr` and `strchr`. `delaunay` now calls
     `fopencookie`, and no longer `fopen`; `fopen`'s callers are `_Py_wfopen`, `Py_fopen`,
     `FT_Stream_Open`, `xsltDocumentElem` and `freopen`.
   - **A guest probe** (EXECUTED, `probes/probe1.py`, through `wasi_python.run` with
     `max_open_files=8` and a writable root holding `dev/`): the program holds 7 files, then
     runs 201 Delaunay triangulations and the collinear error. The 8th open still succeeds, so
     qhull's stream holds no descriptor. `dev/` is still empty afterwards.
   - The memo's fallback form, and released matplotlib, both leave `dev/null` behind. The
     builder saw both fail the no-host-file check (READ, criterion 1). The check lists both
     writable grants before and after, and so catches it (READ).
2. **`fd_renumber` and the 068 cap: counted right, and out of the guest's reach.**
   - **Reach** (EXECUTED, call graph from the name section): the import is called only by
     `__wasi_fd_renumber`. That is called only by `__wasilibc_fd_renumber`, that only by
     `freopen`, that only by `qh_initflags`, and that only by `qh_new_qhull`. matplotlib passes
     the fixed command `qhull d Qt Qbb Qc Qz`, with no `TI` or `TO` option (READ). `os.dup2`
     does not exist in the guest (EXECUTED). Neither `freopen` nor `__wasilibc_fd_renumber` is
     exported or in the function table. So Python code cannot call `fd_renumber`.
   - **If something did call it,** the runner has shadowed and counted it since spec 068
     (`mounts.COUNTED`). With mounts, a renumber onto or from a table number, or a number at or
     above 2**30, answers `ENOTSUP`. Without mounts it is forwarded, and the held set follows
     wasmtime: `to` is closed, and `from` moves there (READ, `_fd_renumber`).
   - I checked every case of held and not held, plus self-renumbers and stdio. None lets the
     count fall while a guest-opened number stays open (INFERRED).
     `test_open_files_are_counted_on_a_call_without_mounts` and
     `test_mount_files_count_toward_the_open_file_cap` exercise these cases against real wasmtime
     and pass (EXECUTED, my record).
   - The descriptor count's change from 28 to 29 is only a tripwire. The gate is the set
     difference against the shadowed and forward-safe calls, and it did not change. The
     `mounts.py` edit is a comment only (READ).
3. **Licences: right.**
   - §4.12 names contourpy, "its GIST-derived code under matplotlib's LICENSE_YORICK; question
     81", approved 2026-10-18. Qhull was approved 2026-10-17 (READ, the constitution).
   - `LICENSES/contourpy.txt` holds contourpy's BSD-3-Clause, then `LICENSE_YORICK` (the
     Regents' 1996 notice). `LICENSES/qhull.txt` holds qhull's `COPYING.txt` (EXECUTED).
   - `MORE_LICENCE` and `BORROWED_LICENCE` judge them by content, not just presence (EXECUTED:
     both are in the content list, and the mutations fail as shown under F6).
4. **Amendment 1, the `_build_config.py` copy: sound, reproducible, host-neutral.**
   - meson's plan gives the file `tag: None` (EXECUTED), so `--tags python-runtime` leaves it
     out. meson-python installs every tag, which is why the wheel has the file.
   - The member in the zip shows only `/wasi-python-build/…` paths, `build_cpu*` set to `build`,
     `host_cpu wasm32` and `mesonpy_version 0+stand.in` (EXECUTED, the `.pyc`'s strings).
   - The host-fact check passes, and it now applies bare `linux` to the member.
   - Three hosts give one `SHA256SUMS` (READ, with my `diff`). F5 is the one gap.
5. **Amendments 8 and 9: measured; see F1.** The zip explains the plain start. The binary
   explains the snapshot start and numpy-core. The `invalidate_caches` mechanism does not occur.
6. **Judge edits outside Decision 9's list: faithful, and none weakens.**
   - The descriptor count (point 2).
   - `test_scan`'s first sorted record is now `contourpy-build` (mechanical).
   - The fixtures in `test_artifact_rules` gain the pins and packages. The host-fact test gains
     the third member, with leaky and missing cases, which is stronger.
   - `packages.toml` contourpy is `later` → 066 (allowed; F4).
   - The licence rules are stronger.
   - `PLATFORM_BOUND` gains `plot_contour`: only the oracle's reproduction is bound to
     darwin-arm64, and the guest must match everywhere, as Decision 8 says.
   - The two removed gaps now pass.
   - No golden, allowance or progress file changed except the new job's golden (READ, the diff).
7. **The 063 rule: met.**
   - contourpy has its `[package.contourpy]` entry, qhull is `via = "matplotlib"`, and
     `test_every_package_names_its_own_suite` passes (EXECUTED).
   - The new checks are in `test_v1_3_matplotlib.py` and `test_v1_2_hostile_guest.py`. Both are
     in `own-guest`, which runs on macOS, Linux and Windows. So the release runs them on
     Windows, which no landing does (READ, `tests/release_shards.toml`).
8. **051's callback scan: green** (EXECUTED). The patch's lambda has the
   `(void*, const char*, size_t) -> ssize_t` shape that musl's `cookie_write_function_t` is
   called with (READ).

**Decision 10's numbers.** `python.wasm` grew by +1,050,573 bytes, 5% over the top of the range
and so within a tenth. The zip grew by 19 members (amendment 2: 18 files plus METADATA,
EXECUTED from the zip's names) and 64,998 bytes. No member besides contourpy's changed
(EXECUTED, CRC by name). There are 44 imports, the only new one is `fd_renumber`,
`wall_errors` is empty, and the 9 constructors are unchanged on both binaries (EXECUTED). The
snapshot `-c pass` row is far outside the inferred +0.05%. Under the rule, that is a finding for
this review, F1, and it is now measured.

## Notes (no action required)

- `run` with a root makes `usr/local/lib` folders in the host root. That is the runner's
  existing behaviour, not 043's. The no-host-file check lists after matplotlib's import, so it
  correctly ignores them.
- `os.dup` exists in the guest, and `os.dup2` does not. Neither reaches `fd_renumber`.
- Spec 081 has landed on main since the base. Its driver guard refuses a measured run whose
  inputs name a host path. 043's new checks pass only guest paths in their argv, env and files
  (READ). The lane's judge will confirm this after the rebase.

## What the lane must do

1. **Fix F1** in the landing notes. Do F2 at the rebase. F3 to F6 may land with it or follow
   (F4 is `context/` only).
2. **Rebase onto main** (`a6dfc17`, with 081 and the 0.1.0a7 release), **after 039 lands**,
   as planned. The two share `scripts/steps/70_zip.sh`, `scripts/assemble_artifacts.py`,
   `tests/harness/paths.py`, `needs.py`, `pins.py`, `tests/known_gaps.toml`,
   `tests/upstream/packages.toml`, `downloads/SHA256SUMS`, README and CHANGELOG.
   - The release workflow's tree count becomes **22**: 19, plus 039's pyyaml and markupsafe,
     plus contourpy (READ, 039's branch: 21).
   - Both entries go under 0.1.0a8.
3. **A full rebuild from pins** on the rebased tree. The zip, the snapshot and every number move
   with 039's members.
   - Record the new numbers.
   - Get a **delta review** if the recipe hunks or numbers moved (AGENTS.md rule 2). My record
     is for this commit's set, so `sameness.py` against my record applies only if the set is
     unchanged.
4. **Judge serially on the exact commit, then accept** with `--accept "<reason>"`,
   `--accept-judge "<Decision 9's judge changes and amendment 5's>"`, and `--accept-growth
   "<F1's measured causes>"`.
5. **The release dry run** on main's exact commit, every job on all three systems (criterion 7;
   rule 6b). This is the first time the new checks run on Windows. The x86_64 rebuild's time
   (spec 040) is recorded there.

## Verdict

**Lands once F1 is fixed:** the landing notes and the accept-growth reason must give the
measured causes. The binary causes the snapshot and upstream-suite growth. The zip causes the
plain start's. The lane also does the rebase after 039, the rebuild, any delta review it needs,
and a green release dry run. F2 is done at the rebase. F3 to F6 are low.

## One line

The milestone is built as specified: the patch is recorded and opens nothing, `fd_renumber` is
unreachable and counted, the licences and host facts are clean, and the judge is reproduced
exactly. But two growth reasons blame the zip, when the measurements show the binary.
