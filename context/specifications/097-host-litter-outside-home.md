# 097 — host litter outside the home folder: the judge's guest folders leave HOME on macOS, and the OpenBLAS script never reads litter

- **Status:** **built 2026-10-20 on `dbecd2d`** (main plus the structural chain 103 to 109;
  code tip `90eed13`, CI run 39532775277; the section "Landing notes"); awaits its build review.
  **Revised 2026-10-20 against its pre-build review** ("build once finding 1 is
  answered in writing": `../reviews/097-host-litter-outside-home-prebuild-2026-10-20.md`; the
  section "Disposition of the pre-build review"). **Drafted 2026-10-20** from main `5805af0`, on
  `spec/097-host-litter-outside-home`. It changes the build recipe (two files under `scripts/`,
  each a `recipe` line of `MANIFEST`) and the judge's guest driver, so constitution §5.6 and
  AGENTS.md rule 8 asked a review before it is built. A different agent reviews the build.
- **Date:** 2026-10-20
- **Owner:** Clay Gendron
- **Kind:** a judge change and a recipe change; **build-class** (§5.7: it touches `scripts/`).
  Edits: `tests/harness/paths.py` (`GUEST_TMP`, `guest_tmp()`), `tests/harness/guest.py`
  (`host_roots_always`), `tests/harness/litter.py` (its messages and docstring),
  `tests/harness/plugin.py` (the leftovers line), `tests/checks/conftest.py` (the `guest_workdir`
  fixture), `scripts/litter.py` (`git_excludes`), `scripts/make_openblas_void_patch.sh` (its `add`
  and its unstage). New: one check in `tests/checks/test_v1_4_embedding.py`; unit rows in
  `tests/unit/test_scipy_build.py`, `tests/unit/test_build_scripts.py` and
  `tests/unit/test_host_litter.py`; one CHANGELOG line. No `src/`, `recipes/`, `downloads/`,
  workflow or README. No existing check, golden, gap or allowance is edited.
- **Depends on:** nothing unlanded. Spec 066 (in wave 08) puts `/tmp/work` in the guest's writable
  root; this spec moves that root, with every other, without touching 066's files (Decision 2).
- **Research it stands on:** `../research/2026-10-19-ds-store-in-the-judges-stages.md` (spec 089's
  memo: the writer, its probe, the refuted symlink); spec 089's landing notes and its accepted
  residual (writable roots are detection-only); spec 081's measurement (a checkout's path length
  moves fuel only through an input that names a host path); spec 066's delta review, L5. New
  evidence here, EXECUTED, in `../research/2026-10-19-ds-store-in-the-judges-stages/for-097/`:
  `race.sh` and `race.out` (the unstage race and its fixes), `tmpfacts.py` and `tmpfacts.out`
  (the per-user temporary folder on this Mac), `probe.sh` and `probe.log` (a 12-minute probe
  under the home folder and in `T`: no litter in either, so inconclusive).

Labels: **EXECUTED** (run here), **READ** (read in code or files), **INFERRED** (reasoned).

## The problem

Spec 089 made host litter harmless in the judge's read-only stages. It seals them: no folder in a
stage keeps a write bit, and macOS's folder-size cache, which runs as the user, respects that. It
also watches every guest run: litter in any grant fails the run with `HostLitter`, and the run
records no fuel. Two holes stayed open, and wave 08's acceptance fell into both while the owner
was away with System Settings' Storage pane and Finder windows open on the checkout.

1. **A writable guest root cannot be sealed.** The guest writes there, so its folders keep their
   write bits. Spec 089 accepted that as a residual: writable roots are watched, not sealed. With
   spec 066, a CPython or package group runs for minutes in a root whose `/tmp/work` the guest
   fills. macOS wrote `.DS_Store` into `/`, `/tmp` and `/tmp/work` of that root. The watch named
   them, and the group was void. A void group measures nothing, so the acceptance could not finish.
   Every such root lives under `build/harness/guest-*`, in the checkout, under the home folder.
2. **The OpenBLAS patch script races the writer.** `scripts/make_openblas_void_patch.sh` runs
   `git add -A --force` on the unpacked tarball, then unstages every litter path with
   `git rm -q --cached -- "$p"` (spec 090). `git rm --cached` refuses a path whose staged content
   differs from both the file and `HEAD`. When macOS rewrites a `.DS_Store` between the add and the
   rm, that is exactly the case. git says "the following file has staged content different from
   both the file and the HEAD: .DS_Store (use -f to force removal)", the script exits 1, and
   `test_the_openblas_patches_are_what_their_script_makes` fails. EXECUTED by hand in `race.out`,
   case 1.

## Principle

A folder a guest sees **unsealed** lives where no desktop writer looks. A folder a guest sees
**sealed** may stay where it is, since the seal holds there. A script that stages a tree for git
**never opens a litter file**, and removes a staged one without asking the work tree. The watch
stays as the backstop: anything that still gets in is named, never filtered and never measured.

## Decisions

1. **Two scratch roots, not one.**
   - `paths.HARNESS_TMP` stays `build/harness`. It holds the host's own work and every sealed
     stage. Every tarball and wheel the judge unpacks is unpacked there, as §4.8 asks
     ("unpack under `downloads/` and `build/`").
   - **New: `paths.GUEST_TMP`**, the root of every folder the judge's driver grants a guest
     unsealed. On darwin it is
     `realpath(tempfile.gettempdir()) / "judge-wasi_python-<k>"`, where `<k>` is the first 12
     hex digits of the SHA-256 of `str(paths.REPO)`. On every other system it **is**
     `HARNESS_TMP`, the same path object, so Linux and Windows see no change at all.
   - **Why the per-user temporary folder.** On this Mac it is
     `/private/var/folders/_c/n40__q_16zs0cbn45nb3c_nw0000gn/T`: mode 0700, owned by the user,
     outside the home folder, on the same volume as the checkout (`st_dev` 16777230 for both)
     (EXECUTED, `tmpfacts.out`). Spec 089's probe saw the writer only under the home folder, and
     never in 40 minutes in a tree outside it (EXECUTED there). This spec's own probe on `T` was
     inconclusive: the writer did not show up in the control either ("The probe" below). The product runner already keeps every call's
     private folder there (READ: `runner._Private`), and the judge already treats it as a host
     root (READ: `guest.host_roots_always`).
   - **Why not `/private/tmp`.** It is shared by every user of the machine, so a fixed name there
     can be taken by someone else first. `T` is this user's alone.
   - **Why not `chflags hidden` in place** (the pre-build review, F1). Spec 089's probe saw one
     fresh hidden folder skipped (memo §1, Variants). That is one observation of one folder. It
     does not show that the writer skips a hidden folder's descendants when they change, and a
     guest's root changes deep inside on every run. Leaving the home folder rests on where both
     writers were seen to work, and on a temporary folder that has never held a writer's
     `.DS_Store` (the pre-build review's survey: 13 `.DS_Store` files among 7,299 entries in `T`,
     every one explained, none of a writer's size). So the folders move. The flag is not set,
     because it would add a second mechanism with no measured benefit outside the home folder.
     It is not set on the unit suite's `work` folders either (the review's optional offer):
     Decision 4's residual stands on its own reasons, and an unmeasured flag would only blur them.
   - **Why `realpath`.** `/var` is a link to `private/var`. The product runner refuses a root that
     passes through a link in a folder the user can write (spec 089's first attempt: 87 checks
     failed through a symlinked `build/harness`). `/var` sits in `/`, which only root can write, so
     the runner would accept it. The real path holds no link at all, which is simpler to trust:
     every component of `/private/var/folders/_c/n40__q_16zs0cbn45nb3c_nw0000gn/T` is a real
     folder (EXECUTED, `tmpfacts.out`, `lstat` of each).
   - **Why that name.** Keyed by the checkout, so two worktrees never share a folder. Not
     `wasi-python-…`: that is the runner's private-folder prefix, its sweep matches lock files by
     it (READ: `runner._LOCK_NAME`), and checks list the temporary folder for it (READ:
     `_entries` in `test_v1_4_embedding.py`).
   - **`paths.guest_tmp()` makes it.** On darwin: `mkdir(mode=0o700, exist_ok=True)`, then an
     `lstat` that must show a real folder (not a link), owned by this user, with no group or other
     bits; otherwise an `AssertionError` names it, and the judge uses nothing there. Elsewhere:
     `HARNESS_TMP.mkdir(parents=True, exist_ok=True)`, today's call.
   - **A `TMPDIR` inside the home folder is not accepted in silence.** The new check (Decision 8)
     fails on darwin when the root it observes is under the home folder, and says to set `TMPDIR`
     outside it. No fallback picks another folder.

2. **What moves, on darwin.** The `guest_workdir` fixture (one per session, `tests/checks/conftest.py`)
   makes its folder under `GUEST_TMP` instead of `HARNESS_TMP`. Everything the driver makes from
   it moves with it, with no other edit:

   | folder | made by | sealed? | after this spec, on darwin |
   |---|---|---|---|
   | a run's writable root `run-N/root` (066's `/tmp/work` inside it) and its `io` | `guest.run` under `workdir` | no | `GUEST_TMP` |
   | a run's stdlib folder `run-N/lib` | `guest.run` | yes | `GUEST_TMP` |
   | matplotlib's data `mpl-data-N` | `guest.mpl_data_dir(…, workdir)` | yes | `GUEST_TMP` |
   | a `Turns` instance's folders | `guest.Turns(…, workdir)` | no | `GUEST_TMP` |
   | every grant and product-runner root a check makes under `guest_workdir` (`ro-`, `rw-`, `data-`, `grants-`, …) | the checks | no | `GUEST_TMP` |
   | the CPython stage `cpython/run-*` | `regrtest.Session` | yes | stays, `HARNESS_TMP` |
   | the upstream stage `upstream/run-*` | `upstream.Session` | yes | stays, `HARNESS_TMP` |
   | the zips `zips-<sha>-v2` | `zips.judge_zips` | never granted (a run clones one into its `lib`) | stays |
   | `openblas-void` | the OpenBLAS check | host only (an unpacked tarball, git) | stays |
   | `patched-*` | `pins.py` | host only (unpacked tarballs) | stays |
   | `oracle-check` | the oracle check | native Python, no guest | stays |
   | `unit-*` | the unit `work` fixture | see Decision 4 | stays |

   READ: every use of `paths.HARNESS_TMP` (`grep -rn HARNESS_TMP tests src scripts`), every
   `mkdtemp` in `tests/`, and the two `Session`s' `workdir` (both get `guest_workdir`,
   `tests/checks/test_v1_3_upstream_suites.py`). Folders under pytest's `tmp_path` are already
   under `T` (pytest's base temp), and the product runner's own private folders are already there.
   So after this spec, on darwin, **every unsealed folder a guest sees is outside the home
   folder**, except the unit suite's (Decision 4).

3. **§4.8, read plainly.** Nothing is unpacked outside `build/`: the stages, the trees and the kit
   wheels stay where they are. A writable root outside `build/` holds what a check writes there and
   what the guest writes. With spec 066 that includes **copies** of a few staged members a check
   names (lxml's three `cwd_files`, matplotlib's baseline images), read only by a guest under
   wasmtime, which §4.8 allows ("execute only … as guests under wasmtime"), and removed with the
   root. The repo's own wording, "never the system's temporary folder (§4.8)" (`pins.py`, the unit
   `work` fixture), is about where downloads unpack, and stays true. **This reading is the one
   point the pre-build review is asked to rule on** (R1 below). If the owner reads §4.8 more
   strictly, the copies must come from a sealed read-only grant instead of the root, which is
   066's change, and this spec is otherwise unchanged.

4. **The unit suite's `work` stays under `build/harness`.** A unit guest is a small module built
   from WAT; its run lasts milliseconds in a fresh folder, while the writer acts 4 to 7 s after a
   change it sees (EXECUTED in spec 089's probe). Unit rows record no fuel, and a `HostLitter` there
   names itself. A named residual, INFERRED from those timings.

5. **Spec 081 still holds, and fuel does not follow the move.**
   - `host_roots_always()` adds `GUEST_TMP`, so a measured run whose input names a host path there
     is refused, in every form `_forms` makes (as written, resolved, `file:` URI). Today `T` is
     already a host root, so on this Mac nothing changes; the addition covers a `TMPDIR` of
     literally `/tmp`, where `host_roots_always` leaves the temporary folder out (READ).
   - **Why fuel cannot move (INFERRED).** A preopen hands the guest a guest path only; the host
     path never reaches it. Spec 081 measured 148 rows in two checkouts, 44 and 205 characters
     long: only a row whose input named a host path moved (EXECUTED there). Spec 083's file facts
     answer every inode number and time the guest reads. What a filestat still carries from the
     host is the device number, the link count, the size and the type. The device number is the
     same for the checkout and `T` on this Mac (EXECUTED, `tmpfacts.out`); the others depend on a
     folder's contents, not on where it is.
   - **The build proves it** (criterion 3): the same fuel-recording rows, on one private set, twice
     with the guest folders under `build/harness` and twice under `T`, every value equal. The
     builder's CI run then compares the macOS legs with `accepted.json`.

6. **The seal and the watch stay as they are.** Each run's grants are still watched; every sealed
   folder is still sealed. Only where the folders live changes. A killed judge now leaves its run
   folders under `GUEST_TMP` on darwin, so `sealed_leftovers` looks under both roots, the plugin's
   session-start line names both, and every `HostLitter` message and the `litter.py` docstring give
   the recovery for both (`chmod -R u+w <folder>` then `rm -rf`), by their real paths.

7. **The OpenBLAS script never opens a litter file, and never asks the work tree to unstage one.**
   - **Excluded at the add.** `scripts/litter.py` gains `git_excludes()`: for each name in
     `OS_LITTER`, `:(exclude,glob)**/<name>` and `:(exclude,glob)**/<name>/**`, and the same two
     for `._*`. The script writes `.` and those, NUL-separated, to `$WORK/add.pathspec` (outside
     the tree) once, and both adds become
     `g add -A --force --pathspec-from-file="$WORK/add.pathspec" --pathspec-file-nul`. git then
     never opens a litter file, so a file the writer rewrites, truncates or removes mid-add cannot
     fail the add. EXECUTED (`race.out`): an unreadable `.DS_Store` fails a plain `git add -A
     --force` with "error: open(".DS_Store"): Permission denied … fatal: adding files failed"
     (case 4), and the excluded add passes and stages neither `.DS_Store` nor `sub/._a.c` (case 5).
     `--pathspec-from-file` needs git 2.26 or later. The OpenBLAS check runs `/usr/bin/git` (its
     `PATH` is `/usr/bin:/bin:/usr/sbin:/sbin`): Apple Git 2.50.1 on this Mac, which the review ran
     the excludes with (EXECUTED there); `race.out` used Homebrew's 2.51.0 from the shell's
     `PATH`. The script's `GIT_CONFIG_GLOBAL` already needs 2.32.
   - **Forced at the unstage.** The unstage stays, with `has_litter` as the one authority, but
     each staged litter path leaves the index by `g update-index --force-remove -- "$p"`, which
     compares nothing with the work tree. EXECUTED (`race.out`): after a rewrite, `git rm --cached`
     fails (case 1), `update-index --force-remove` passes (case 2), and so would `git rm --cached
     -f` (case 3). With the excludes it should never find one; a unit row holds the two rules equal
     (Decision 8), and the unstage remains so a disagreement can never put litter in a patch.
   - **Siblings.** `make_openblas_void_patch.sh` is the only place in `scripts/` or
     `tests/harness/` that adds and then unstages (READ: `grep -rn "rm --cached\|git add\|add -A\|update-index"`).
     `apply_patches.sh` runs `git apply`, which reads no untracked file; `assemble_artifacts.py`
     runs `git ls-files`; the patched-tree comparison in `pins.py` skips litter by name (spec 090).
     None of them races the writer.
   - **The set changes by two recipe lines.** Both files are tracked under `scripts/`, so each is a
     `recipe <sha> <path>` line of `MANIFEST` (READ: `assemble_artifacts.py`, `git ls-files recipes
     scripts`). `MANIFEST` changes, and with it the set's `SHA256SUMS`. `python.wasm`, the snapshot
     and the stdlib zip are byte for byte the same (INFERRED: neither file is compiled or zipped;
     the build compares their hashes, criterion 4). The three carried OpenBLAS patches do not
     change: the tarball holds no litter name (the script checks), so the excludes leave out
     nothing it holds.

8. **Checks first, each seen failing on main's code.**
   - **`test_the_judges_writable_roots_are_outside_the_home_folder`** (`test_v1_4_embedding.py`,
     goal v1.4, beside spec 089's drop check). No artifact: it runs a WAT command
     (`harness.wat.COMMAND_EXIT_7`) through the judge's driver in `guest_workdir`, unmeasured, and
     looks at the root the run was given. On darwin, in this order: the root's real path is its
     path (no link anywhere); it is not under the home folder (comparing real paths, since `HOME`
     may hold a link); and only then, it is under `paths.GUEST_TMP`, and `GUEST_TMP` is on the
     same device as `HARNESS_TMP` (else it fails naming both folders and their devices, and says
     to set `TMPDIR` to a folder on the checkout's volume outside the home folder: criterion 3's
     fuel proof covers one device; the pre-build review, F4). Elsewhere: it is under
     `paths.HARNESS_TMP`, as today. On main it fails on darwin with "a root under the home
     folder", naming one under `build/harness`, not with an `AttributeError` (the order: the
     review's N5); on Linux and Windows it passes on main too, which is the point.
   - **`test_the_openblas_patch_script_survives_litter_rewritten_after_its_add`**
     (`test_scipy_build.py`, beside spec 090's row and on its stand-in layout). A `git` wrapper
     first on `PATH` (the script's `env -i` keeps `PATH`) writes `.DS_Store` into the tree and a
     subfolder just before each `add`, runs the real git, then rewrites both. On main's script it
     fails with git's "staged content different from both the file and the HEAD"; with the fix the
     patches are made and name no litter. The race is simulated deterministically: the rewrite
     always lands between the add and the unstage.
   - **`test_the_openblas_patch_script_never_reads_host_litter`** (the same layout). The wrapper
     makes those `.DS_Store` files unreadable before each `add` and readable after. On main it fails
     with "Permission denied"; with the fix it passes. Skipped on Windows and as root, where a mode
     does not stop a read.
   - **`test_the_openblas_patch_script_unstages_litter_its_add_staged`** (the same layout; the
     pre-build review, F2). The wrapper drops `--pathspec-from-file=…` and `--pathspec-file-nul`
     from each `add`, so the add stages the planted `.DS_Store` files as if the excludes missed
     them, and it rewrites them after the add. With `git rm -q --cached` in `unstage_litter` it
     fails with git's "staged content different from both the file and the HEAD"; with
     `update-index --force-remove` the patches are made and name no litter. Its seen-failing line
     is taken on the branch's script with only the unstage reverted. So each of the two script
     changes has a row that fails without it.
   - **The wrappers exec the git the script would find** on the row's `PATH` (the review's N7),
     resolved by `shutil.which("git")` before the wrapper folder is put first.
   - **Unit rows:** `git_excludes()` and `has_litter` agree on a tree of yes and no names through
     real git (`test_build_scripts.py`: `.DS_Store` at the top and deep, `._x.c`, `Icon\r` where the
     platform allows it, a file inside `.Trashes/`, and `DS_Store`, `x._y`, `Icon`,
     `.DS_Store.bak`, `.gitignore` kept); `paths._guest_tmp_for(repo, temp, platform)` gives two
     checkouts two folders, a real path under the temporary folder on darwin and `build/harness`
     elsewhere; `guest_tmp()` refuses a link and a folder with group or other bits;
     `host_roots_always()` holds `GUEST_TMP` (`test_host_litter.py`).

### The probe (EXECUTED, `probe.log`)

Two identical trees, shaped like a run's root and stdlib folder: one under the home folder (this
worktree's `build/097-probe`), one in `T`. Both were changed every 5 s for 12 minutes, 14:59 to
15:22 on 2026-10-20. **Neither got a `.DS_Store`** (`home tree litter: 0`, `temp tree litter:
0`). **So the probe settles nothing.** The control under the home folder got none either, so the
writer was not active, or did not scan this worktree, which sits under the dot-folder `.claude/`.
The case for `T` therefore rests on spec 089's EXECUTED probe (a tree under the home folder got a
`.DS_Store` within 7 s; the same tree under `/private/tmp` got none in 40 minutes), and on what
the writer was seen to scan (the home folder, `~/Git/Repos`). That `T` in particular is never
scanned is INFERRED: it is outside the home folder, like `/private/tmp`.

The pre-build reviewer's probe (`probe3.log`, 17 minutes, three trees: under the home folder, in
`T`, under `/private/tmp`) also found none in any tree, while the writer was active and sized the
control from its parent. What does settle something is the reviewer's passive survey: `T` holds
7,299 entries and 13 `.DS_Store` files, every one explained (unit rows' plants, a hard-linked git
object, a disk image, a 0-byte copy), none of a writer's size; the main tree holds 176 under
`build/` alone. **A probe counts only if its control under the home folder gets a `.DS_Store`**;
two have failed that rule, and none is a criterion of this spec. The watch stays as the backstop
(Decision 6).

## Intent

On macOS, no folder a guest sees unsealed lies under the home folder, so the desktop's folder-size
cache never reaches one, and the watch stays to name anything else. The OpenBLAS script never
opens a litter file and never needs the work tree's agreement to unstage one, so a desktop writer
cannot fail it. On Linux and Windows nothing changes.

## Design

- `paths.py`: `_guest_tmp_for(repo, temp, platform)` (pure), `GUEST_TMP = _guest_tmp_for(REPO,
  tempfile.gettempdir(), sys.platform)`, and `guest_tmp()` (makes and checks it; returns it).
- `tests/checks/conftest.py`: `guest_workdir` calls `paths.guest_tmp()` and makes its `guest-*`
  folder there.
- `guest.host_roots_always()`: adds `paths.GUEST_TMP` when it is not `HARNESS_TMP`.
- `litter.py`: the recovery text names `paths.HARNESS_TMP` and, when different, `paths.GUEST_TMP`.
  `plugin.py`: `sealed_leftovers` over both, one line naming both.
- `scripts/litter.py`: `git_excludes()`. `make_openblas_void_patch.sh`: writes the pathspec file
  after `g init`, adds through it, unstages with `update-index --force-remove`.
- The new check and unit rows of Decision 8.

## Scope

In: Decisions 1 to 8.

Out, and why:
- **The stages stay under `build/harness`.** They are sealed, the seal held against the real
  writer in spec 089's build (it took a `.DS_Store` written during staging), and moving them
  would unpack tarballs and wheels outside `build/` (§4.8, Decision 3).
- **The roadmap's other two 097 items stay reserved:** `test_elementsoup.py` under pytest's import
  mode, and the `stage-layout` class (spec 066's tables). Neither is on main (066 is in wave 08,
  unlanded). Both mean staging a package's tests inside its package folder, which moves
  matplotlib's and lxml's fuel and needs its own measurement; not small. Their closers point at
  `context/roadmap.md`, not at this file (READ: `tests/upstream/lxml.toml`, `matplotlib.toml` on
  `wave/08`), so nothing in the judge names 097. The lane gives them a number.
- **The unit `work` fixture** (Decision 4).
- **Which process writes the files** (spec 089 left it open; it does not matter here).

## Acceptance criteria

1. **The checks fail first.** On main's code (the branch's checks over `5805af0`'s harness and
   script): the root check fails on darwin, naming a root under `build/harness`; the rewrite and
   unreadable script rows fail with git's "staged content different from both the file and the
   HEAD" and "Permission denied"; the forced-unstage row fails, on the branch's script with only
   the unstage reverted, with "staged content different"; the unit rows fail to find `GUEST_TMP`, `_guest_tmp_for` and
   `git_excludes`. The lines are in the landing notes.
2. **They pass with the build,** with `ruff check` and `ruff format --check` green.
3. **Fuel is location-free (EXECUTED at build).** On one private APFS copy of a frozen set (every
   file at link count 1), these rows run twice on main's code (guest folders under
   `build/harness`) and twice on the build (under `T`), by node id, serially:
   `test_a_file_dropped_into_a_stage_changes_nothing` and
   `test_file_facts_cost_the_same_on_every_run` and
   `test_fuel_does_not_follow_the_stdlib_zips_link_count`, each on both binaries;
   `test_matplotlib_data_is_granted_read_only` on both;
   `test_upstream_suite[cpython-fs]`, `[cpython-archives]` and `[numpy-lib]`; and the numpy and
   pandas jobs of `test_v1_3_data_stack.py`. Every row gives one fuel value across the four runs.
   A row that differs between two runs of the same code is noise, not location, and is named.
   A leg that ends in `HostLitter` measured nothing: it is run again, and the landing notes name
   it. The main's-code legs run from a `git clone --local` of the base outside the home folder
   (its guest folders then under its own `build/harness`, at a second location), so the writer
   cannot void them; that is what the comparison needs, the same code at two locations (the
   pre-build review, F3).
4. **The set.** After a rebuild (the lane grants the slot), `MANIFEST` differs from the base set's
   in exactly the two recipe lines, and `python.wasm`, `python-snapshot.wasm` and
   `python-stdlib.zip` have the base set's hashes.
5. **The OpenBLAS check,** `test_the_openblas_patches_are_what_their_script_makes`, passes against
   the real pinned tarball: the same three patches, byte for byte.
6. **Nothing else moves.** The fast tier (`-n 3`, on a slot the lane grants): no failure, no lost
   pass, no fuel row past its tolerance; gained, the new check; `judge changed`. The builder's
   release workflow run: every job green; the macOS legs' fuel inside the tolerance of
   `accepted.json` (the move, measured on CI); Linux and Windows rows as before.
7. **Cleanup.** After the full judge, no `guest-*` folder of that run is left under `GUEST_TMP`,
   and no folder under either root lacks its owner's write bit.

## For the pre-build reviewer: the risks

- **R1, §4.8 (Decision 3).** After 066, a writable root outside `build/` holds copies of a few
  tarball members. Is "copies handed to a guest under wasmtime" within §4.8, or must they come
  from a sealed grant? **Ruled within §4.8 by the pre-build review**, which adds the stronger
  precedent: the product runner already copies the stdlib zip and extracts matplotlib's data
  into its private folder under `T` on every call. No owner answer is needed; the owner may put
  it on record (the review's optional question 1).
- **R2, a host fact that follows the location.** A filestat's device number reaches the guest. On
  this Mac it is the same for both places; on a host where `T` is another volume it would differ.
  The repeats (criterion 3) measure this Mac; the CI run measures GitHub's macOS runner.
- **R3, macOS cleans `T`.** INFERRED: the system removes items in `T` not used for some days, as
  root. A session's folders are fresh, so none of a live run's should go; `guest_tmp()` re-makes
  the base folder each session. Leftovers a killed judge sealed are removed by it too, which is a
  gain.
- **R4, the product runner inside `T`.** Its rules refuse a grant at or above the temporary
  folder and a writable grant inside its own stdlib or private folders (READ: `_judge`,
  `_shared_folders`, `_runtime_folders`); `GUEST_TMP` is a sibling of those. Its sweep acts only on
  lock files named `wasi-python-*.lock`. The fast tier is the proof, since spec 089's symlink failed there.
- **R5, the git version.** `--pathspec-from-file` needs git 2.26 or later on every host that runs
  the script (the macOS and Linux build hosts). Moot in practice (the review): the script's
  `GIT_CONFIG_GLOBAL` already needs 2.32; this Mac's `/usr/bin/git` is 2.50.1; the runners'
  versions are INFERRED from their images, and the CI run shows them.
- **R6, the unit suite's residual** (Decision 4), and the stages staying under the home folder,
  sealed (Scope).
- **R7, `T` itself is not proven clean.** No probe has met the writer anywhere, so the case for
  `T` rests on spec 089's `/private/tmp` probe, on where the writer was seen to scan, and on the
  review's survey of `T` (INFERRED). The watch stays, so if that inference is wrong a run is
  voided by name, never measured wrong.
- **R8, `TMPDIR` set by a user** to a folder under the home folder, or on another volume than the
  checkout: the check fails, by design, naming it; there is no fallback.

## For the lane

- **Build-class.** It needs a rebuilt set for criterion 4 (`MANIFEST`'s two recipe lines), a
  native build slot, and one CI run. Its CHANGELOG line goes under the unreleased section: "The
  OpenBLAS patch script no longer fails when macOS rewrites a `.DS_Store` in the unpacked tree;
  the judge's guest folders live outside the home folder on macOS (spec 097)."
- **Accept with** `--accept-judge "spec 097: on darwin the judge's guest folders (guest_workdir:
  each run's root, io, stdlib folder, matplotlib's data, Turns, every check-made grant) live under
  paths.GUEST_TMP in the per-user temporary folder, outside the home folder; the stages stay
  sealed under build/harness; host_roots_always holds GUEST_TMP; one new check,
  test_the_judges_writable_roots_are_outside_the_home_folder; unit rows; no existing check,
  golden, gap or allowance edited"` and `--accept "spec 097: scripts/make_openblas_void_patch.sh
  adds with litter excluded and unstages with update-index --force-remove; scripts/litter.py
  gains git_excludes; MANIFEST's two recipe lines"`.
- **The expected record:** gained, the new check; lost 0; grew 0; `judge changed`.
- **The roadmap's 097 line** becomes this spec; its two staging items get the next free number.

## Disposition of the pre-build review

The review (`../reviews/097-host-litter-outside-home-prebuild-2026-10-20.md`, on `e12a5b1`):
"build once finding 1 is answered in writing". Each finding is answered here.

- **F1 (Medium, `chflags hidden` not weighed): answered.** Decision 1 gains the bullet "Why not
  `chflags hidden` in place", in the review's words, with the survey's numbers. The flag is not
  set anywhere, the unit suite's `work` included (the optional offer declined, with its reason).
- **F2 (Low, the forced unstage had no failing row): fixed.** Decision 8 gains
  `test_the_openblas_patch_script_unstages_litter_its_add_staged`, whose wrapper drops the
  excludes; criterion 1 names its seen-failing line, taken with only the unstage reverted.
- **F3 (Low, main's-code legs could be voided): fixed.** Criterion 3: a `HostLitter` leg is run
  again and named; main's-code legs run from a `git clone --local` of the base outside the home
  folder.
- **F4 (Low, R2 not checked): fixed.** The root check asserts, on darwin, that `GUEST_TMP` and
  `HARNESS_TMP` share a device, and fails naming both and their devices. A checkout on an
  external disk then needs `TMPDIR` on that disk, outside the home folder; that is the price of
  a fuel proof that covers one device, and R8 names it.
- **N5 (the root check's order): applied.** Decision 8 orders the assertions so that main fails
  on "under the home folder", not on an `AttributeError`.
- **N6 (Decision 4's §4.8 clause): applied.** The sentence is gone.
- **N7 (the git version): applied.** Decision 7 names `/usr/bin/git` (Apple Git 2.50.1) as the
  git the check runs; the wrappers exec the git found on the row's `PATH`.
- **N8 (leftovers and the disk): noted for the lane.** The lane's disk check names `GUEST_TMP`
  as well as `build/`; no spec change.
- **N9 (R numbering): applied.** R7 and R8 are in order.
- **R1 (§4.8): ruled within it by the review;** R1 says so.
- **The review's probe:** "The probe" section records it and the rule that a probe counts only if
  its control gets a `.DS_Store`. The two probe trees the reviewer left
  (`~/Git/Repos/wasi_python-097-review-probe`, `T/judge-097-review-probe`) are outside this
  worktree; I leave them for the owner or the lane. This spec's own probe trees
  (`build/097-probe` here, and `T/wasi-python-097-probe`) are the same; the first goes with the
  worktree, the second is for the lane.

## Landing notes

**Built 2026-10-20 on `dbecd2d`** (branch `claude/gallant-ride-9nxxmn`: main `faa9c93` plus the
structural chain 103 to 109, which main fast-forwards to tonight). Code tip `90eed13`; CI run
**39532775277** on it. Evidence: `../research/2026-10-19-ds-store-in-the-judges-stages/for-097/at-build/`.
The first half of the build (checks first, the fix, criterion 3's fuel legs) was done on main
`5805af0` by the previous builder session; this session rebased it and finished it.

### What was built

- `paths.GUEST_TMP`, `_guest_tmp_for`, `_make_guest_tmp`, `guest_tmp()`; the `guest_workdir`
  fixture there; `host_roots_always` holds `GUEST_TMP`; `litter.scratch_roots()`, the recovery
  texts and the plugin's leftovers line name both roots (Decisions 1, 2, 5, 6).
- `scripts/litter.py` `git_excludes()`; `make_openblas_void_patch.sh` adds through the excludes
  file and unstages with `update-index --force-remove` (Decision 7). The CHANGELOG line.
- The checks of Decision 8: the root check; three script rows; the parity row; three
  guest-folder rows.

### Rebase

- **Wave 09 (2026-10-21):** onto `spec/100-numpy-on-openblas` at `d5c76bb` (100 rebased onto
  main `58f108f`), from `dbecd2d`, by `git rebase --onto`. **No conflict hunk**: git applied all
  eight commits cleanly, `CHANGELOG.md` included (097's line stays after 066's; 100's lines are
  untouched). 097 changes neither `tests/harness/scan.py` nor `tests/unit/test_scan.py`. After it:
  `ruff check` and `ruff format --check` green; `test_rules.py`, `test_scan.py`,
  `test_scipy_build.py`, `test_host_litter.py`, `test_build_scripts.py` and `test_guest.py`:
  418 passed, 5 skipped (EXECUTED). No new CI run (the lane's ruling; the wave's dry run is the
  check).
- **Wave 09, again (2026-10-21):** onto 100's new tip `8e7eac9` (the oracle's `uv.lock`), from
  `d5c76bb`. **No conflict hunk.** `ruff check`, `ruff format --check` and `test_rules.py`
  (57 passed, 1 skipped) green (EXECUTED). No CI run.
- Onto `dbecd2d` from `5805af0`. Four conflict hunks, all in `27253fe` (the fix commit), each
  resolved keeping both sides:
  1. `CHANGELOG.md`, the unreleased section: the chain's seven lines (103 to 109) and 066's and
     099's, then 097's line after 066's.
  2. `tests/harness/guest.py`, `host_roots_always`'s docstring: the chain's wording (no spec
     number) with 097's clause, "and the judge's guest folders, wherever they are", in words.
  3. `tests/harness/litter.py`, the module docstring's recovery sentence: 097's two scratch
     roots, in words.
  4. `tests/harness/plugin.py`, the leftovers line: 097's loop over `scratch_roots()`; its
     comment without the spec numbers, as the chain's wording has it.
- After the rebase, spec 109's rule (`test_code_outside_src_names_no_context_document`) found
  22 citations in this branch's new comments and docstrings (`spec 097`, `spec 089's`, `§4.8`,
  `F2`, "pre-build review", in `conftest.py`, `test_v1_4_embedding.py`, `paths.py`,
  `test_build_scripts.py`, `test_host_litter.py`, `test_scipy_build.py`, `scripts/litter.py`,
  `make_openblas_void_patch.sh`). Each reworded in words, commit `90eed13`; 0 left (EXECUTED).
  No code, string literal or check changed. The rewording of the two scripts changes their
  `MANIFEST` recipe hashes, which this spec changes anyway.

### Criteria (EXECUTED unless labelled)

1. **The checks failed first** on main's code (`first-fail-*.txt`, on `5805af0`). The root check:
   "a writable guest root under the home folder: …/build/harness/guest-tk1wxo35/run-0/root".
   Rewrite row: "staged content different from both the file and the HEAD". Unreadable row:
   "error: open(".DS_Store"): Permission denied". The forced-unstage row, on the branch's script
   with only the unstage reverted, failed alone with "staged content different"
   (`first-fail-unstage-reverted.txt`). The unit rows failed on `_guest_tmp_for`, `GUEST_TMP` and
   `git_excludes`. The Linux and Windows branch of the root check passes on main too, by design
   (Decision 8); CI ran it on all three systems: pass on each.
2. **They pass with the build.** After the rebase: `test_rules.py`, `test_scipy_build.py`,
   `test_host_litter.py`, `test_build_scripts.py`, `test_guest.py`: 168 passed, 6 skipped, the
   only blocked rows needing artifacts or prior-art clones. `ruff check` and `ruff format --check`
   on `src` and `tests`: green.
3. **Fuel is location-free** (on `5805af0`, the previous session). Every fuel row gave one value
   across four legs (two of main's code from a clone outside the home folder, two of the build
   with its guest folders under `T`): drop check plain 218,765,145, snapshot 20,981,332; file
   facts plain 223,703,451, snapshot 25,878,984; zip link count plain 334,546,494, snapshot
   21,225,960; numpy CSV job 4,996,759,427; pandas CSV job 5,105,780,200; `cpython-fs`
   62,324,809,402; `cpython-archives` 165,638,282,607. The matplotlib rows record no fuel and
   passed; `numpy-lib` was blocked on every leg ("upstream kit"). No leg voided. INFERRED for the
   rebased tip: the chain changes no fuel (its specs say so), and CI run 39532775277 has no
   GREW line.
4. **The set** (`criterion-4.txt`): run 39532775277's release tarball against the main tree's set
   rebuilt at `dbecd2d` (SHA256SUMS `83789790`). `python.wasm` `ee45b241…`, the snapshot
   `9c2af970…` and the zip `fb12a1e6…`: the base's hashes. `MANIFEST` differs in exactly two
   lines, the `recipe` lines of `scripts/litter.py` and `scripts/make_openblas_void_patch.sh`;
   `SHA256SUMS` only in its `MANIFEST` line (`c1cc11ba`); `LICENSES` the same. No local rebuild
   (the lane's ruling).
5. **The OpenBLAS check** passed against the real pinned tarball (`openblas-check.txt`, the
   previous session), and in CI run 39532775277 (pass, darwin-arm64).
6. **Nothing else moves.**
   - The fast tier, `-n 3`, on `90eed13` against a `cp -c` clone of the main tree's set
     (`fast-tier-90eed13.txt`): 2612 passed, 43 skipped, 1 failed. The failure is the expected
     one: `test_manifest_recipes_match_the_tree`, "stale artifact: scripts/litter.py …;
     scripts/make_openblas_void_patch.sh", since the copied set's `MANIFEST` was built from the
     base's two scripts. Lost 1 (that row, the same cause), grew 0, gained 15: the new root
     check and fourteen rules rows of the unaccepted chain 103 to 109. The fast tier compares
     with `accepted.json` of main `faa9c93`, so the chain's rows count as gained here.
   - **CI run 39532775277** on `90eed13`: every job green but `judge (windows-2025,
     own-embedding)`, which failed `test_a_forked_child_is_refused` ("At index 1 diff: 'True
     False' != \"{'used': True, 'forked': False}\""). **That failure is the base's**: the chain's
     own run 39530569266 on `dbecd2d` fails the same job on the same check with the same diff.
     097 touches no runner or fork code. The failed job skipped the gather, so I gathered the 33
     shard records locally with the build's hashes (`ci-39532775277-gather.txt`): red lines G4
     and G5 for that one Windows row, and G7; **no GREW line**, so the macOS legs' fuel is inside
     `accepted.json`'s tolerance with the guest folders moved. 772/865 pass, 1 fail.
   - The earlier run 39487633271 on `27253fe` (before the rebase): every shard green, the gather
     red on G7 only.
7. **Cleanup** (partly). After the fast tier: `GUEST_TMP`
   (`T/judge-wasi_python-11909bf415b5`) is empty, as it was before the run, and `find` found no
   folder without its owner's write bit under it or under `build/harness`. The full judge's
   cleanup is the lane's to read at its acceptance; CI's runners are discarded and record none.

### For the lane

- **Wave kind:** build-class (two files under `scripts/`, two `MANIFEST` recipe lines). Base
  `dbecd2d`. A dry run needs nothing extra.
- **The base's red row.** `test_a_forked_child_is_refused` fails on Windows on `dbecd2d` itself
  (run 39530569266). It is not this spec's; it blocks any wave on this base until the chain's
  fix lands. 097 claims no change to it.
- **The rebuild.** The set changes in `MANIFEST`'s two recipe lines only (criterion 4); the
  lane's set must be rebuilt (or its `MANIFEST` regenerated by the build) before acceptance, or
  `test_manifest_recipes_match_the_tree` is red, as in this fast tier.
- **Claim list:** gained `tests/checks/test_v1_4_embedding.py::test_the_judges_writable_roots_are_outside_the_home_folder`;
  the unit rows of Decision 8 (unit suite); lost 0; grown 0; retired 0; no pass moved. Judge
  changed: `tests/harness/paths.py`, `guest.py`, `litter.py`, `plugin.py`,
  `tests/checks/conftest.py`, `test_v1_4_embedding.py`, and the three unit files.
- **Flags:** `--accept "097: scripts/make_openblas_void_patch.sh adds with litter excluded and
  unstages with update-index --force-remove; scripts/litter.py gains git_excludes; MANIFEST's two
  recipe lines" --accept-judge "097: on darwin the judge's guest folders (guest_workdir: each
  run's root, io, stdlib folder, matplotlib's data, Turns, every check-made grant) live under
  paths.GUEST_TMP in the per-user temporary folder, outside the home folder; the stages stay
  sealed under build/harness; host_roots_always holds GUEST_TMP; one new check,
  test_the_judges_writable_roots_are_outside_the_home_folder; unit rows; no existing check,
  golden, gap or allowance edited"`. No `--accept-growth`.
- **The roadmap's 097 line** becomes this spec; its two staging items (`test_elementsoup.py`
  under pytest's import mode, the `stage-layout` class) need the next free number.
- **Leftovers:** the probe trees named in the Disposition, for the lane.

### The builder's self-check

- [x] rebased onto the named stacked base `dbecd2d` today; the base is in these notes' first line.
- [x] CI run 39532775277 dispatched on `90eed13` and read: red lines G7, and G4 and G5 for the
  base's Windows fork row (the base's own run 39530569266 has it too); no GREW; the new check
  passes on Windows, Linux and macOS.
- [x] every number from a measured run, labelled EXECUTED; criterion 3's legs on `5805af0`, named
  as such; the growth list is empty.
- [x] "For the lane": the claim list, the exact flags, each reason beginning "097:", the wave kind.
- [x] every new check seen failing first; the root check's Linux and Windows branch passes on
  main by design, named.
- [x] no gap; the two reserved staging items need a roadmap number, named for the lane.
- [x] `packages.toml`: no package added; no README row changes.
- [x] CHANGELOG under the one unreleased section; no question for the owner.
- [x] `ruff check`, `ruff format --check`, the fast tier: output in `build/097/` (the fast tier's
  one red row is the copied set's stale `MANIFEST`, named above).

One line: on macOS the judge's unsealed guest folders leave the home folder, where the desktop
never writes, and the OpenBLAS script stops racing it.
