# Review of 097 — host litter outside the home folder (the specification, before build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I wrote none of 097, 089, 090, 066 or the code they touch. Time box: the lane's; the README's 45 minutes for build-class work.
- **Reviewed:** the draft at `e12a5b1` on `spec/097-host-litter-outside-home` (worktree `.claude/worktrees/agent-aee0e93a4a535efef`), base `origin/main` `5805af0`, with wave 08's `wave/08` (`72bc5ed`: 042, 066, 099) read for spec 066's writable root. The local `main` ref in the main tree is stale (`958a22b`); I read against `origin/main`.
- **Read:** `AGENTS.md`; constitution §4.8, §4.14, §5.2, §5.6; the spec and its `for-097/` evidence (`race.sh`, `race.out`, `tmpfacts.py`, `tmpfacts.out`, `probe.sh`, `probe.log`); spec 089's memo (§1 to §3, the probe table). Code: `tests/harness/paths.py`, `guest.py` (`_place`, `mpl_data_dir`, `FileFacts`, `host_paths_in`, `host_roots_always`, `run`, `Turns`), `litter.py`, `plugin.py` (the leftovers line), `upstream.py` and `regrtest.py` (`Session`), `zips.py`, `pins.py`, `jobs.py`; `tests/checks/conftest.py`; every `mkdtemp`, `gettempdir` and `HARNESS_TMP` in `tests/` and `src/`; `wave/08:tests/harness/packages.py` and its `lxml.toml` and `matplotlib.toml`; `src/wasi_python/runner.py` (`_walk_posix`, `_writable`, `_judge`, `_runtime_folders`, `_shared_folders`, `_LOCK_NAME`, `_sweep_entry`, the mounts placeholder); `scripts/make_openblas_void_patch.sh`, `scripts/litter.py`, `scripts/openblas_make_void.py`; `tests/checks/test_v1_5_rebuild_from_pins.py` (the OpenBLAS check); `.gitignore`; `.github/workflows/release.yml` (`runs-on` lines).
- **Run:** no judge tier (the lane holds `build/lane.lock`), no build, no dispatch. This is a specification review; the build review dispatches.
- **Re-ran (EXECUTED, darwin-arm64, everything in my scratchpad `…/scratchpad/097-prebuild/`, except two probe trees named below):**
  - `gitx/run.sh`: Decision 7's pathspec excludes with the git the check really runs (`/usr/bin/git`, Apple Git 2.50.1; the check's `PATH` is `/usr/bin:/bin:/usr/sbin:/sbin`).
  - `probe3.sh` / `probe3.log`: three identical trees changed every 5 s for about 17 minutes, 15:25 to 15:42, while the writer was active (below).
  - Read-only `find`/`stat` of `.DS_Store` files in the main tree (no write; its `build/` was not touched), in sibling worktrees, and in the per-user temporary folder `T`.

## What holds

- **The split is right, and complete as READ.** Every unsealed folder a guest is granted comes from `guest_workdir` (directly, or through `guest.run`, `Turns`, `mpl_data_dir`, and the three `Session`s, which all take `guest_workdir`: `test_v1_3_upstream_suites.py:30-47` on `wave/08`), or from pytest's `tmp_path`, which is already in `T` (EXECUTED: `T/pytest-of-claygendron/`). The remaining `HARNESS_TMP` users are host-only or sealed: the three stages (`cpython/run-*`, `upstream/run-*`, and 066's `upstream-<pkg>/run-*`, each `litter.seal`ed), `zips-*` (cloned into a run's `lib`, never granted), `patched-*`, `openblas-void`, `oracle-check`, 066's `streams/` (host-only stream copies), and `unit-*` (Decision 4). The judge's module cache is `build/cwasm-cache` (host only). I found no check that grants a folder under `paths.REPO` or `paths.BUILD` directly. So after 097, on darwin, the only guest-visible unsealed folders under the home folder are the unit suite's, as Decision 4 says.
- **The product runner accepts roots under `GUEST_TMP` (READ).** `_walk_posix` refuses a link only in a folder this user can write; `realpath(T)` has no link at all (EXECUTED, `tmpfacts.out`; and even `/var` sits in root-owned `/`). `_shared_folders` refuses a grant at or above `T`; `_runtime_folders` refuses a writable grant at, inside or above the runtime's stdlib folder (`T/wasi-python-zip-…`), or above `T` before it exists. `GUEST_TMP` is below `T` and a sibling of the runner's folders, so none applies. The sweep matches only `wasi-python-(root-|zip-)?<16 hex>.lock` (`runner.py:784`); `judge-wasi_python-<k>` never matches, and the checks that list `T` filter on `wasi-python-` (`test_v1_4_embedding.py:1217`, `:1526`, `:1600`). Spec 089's 87 failures came from a symlinked `build/harness` inside the user-writable checkout; that cannot recur here.
- **Criterion 3's rows cover every kind of recorded fuel (READ).** Only the `guest` fixture (`conftest.py:96`) and the suites' `Session`s record `fuel`; product-runner and `Turns` rows record none (the runner's clock is real: `test_v1_3_data_stack.py:268`). So moving their folders cannot move a recorded value, and the list needs no runner row.
- **`realpath` is the right call** for a second reason the spec does not give: a judge run as root would find `/` writable, and then even `/var` would be refused.
- **Host path length is inside what worktrees already prove.** A run root under `GUEST_TMP` is 115 characters; under this worktree's `build/harness` it is 124, and worktree judges pass. No check binds an `AF_UNIX` socket under the work folder (READ).
- **Decision 7 is correct (EXECUTED, `gitx/run.sh`, Apple Git 2.50.1).** With `.` plus the two excludes per `OS_LITTER` name and for `._*`, from a NUL file, `git add -A --force` stages exactly `.DS_Store.bak`, `.gitignore`, `DS_Store`, `Icon`, `keep.c`, `sub/keep.c`, `x._y`, and leaves out `.DS_Store` (top and two deep), `sub/._x.c`, `._top`, `.Trashes/inside`, `._d/f`, `Icon\r` (top and deep), `Thumbs.db`, `sub/desktop.ini`: the same verdicts as `has_litter`. The add passes with two unreadable `.DS_Store` files. After a rewrite, `git rm -q --cached` exits 1 with git's "staged content different" and `update-index --force-remove` exits 0. The only other script that stages is `history.py`'s lane step, which adds named progress paths (READ).
- **R5 is moot in practice.** The script already sets `GIT_CONFIG_GLOBAL`, which takes effect only from git 2.32, so its byte-for-byte check already assumes a git newer than 2.26. It runs only from the OpenBLAS check and its unit rows, where a source tree exists (READ: no step script calls it, so the container build never runs it). Hosts: this Mac `/usr/bin/git` 2.50.1 (EXECUTED); `macos-15` Xcode's Apple Git, `ubuntu-24.04(-arm)` 2.43 or newer, Debian trixie 2.47 (INFERRED from the images). The spec's "this Mac: 2.51.0" is Homebrew's git on the shell's `PATH`, not the one the check runs (N3).
- **`T` has never held a writer-made `.DS_Store` (EXECUTED, read-only survey).** `T` holds 7,299 entries and 13 `.DS_Store` files. Every one is explained: 10 are unit rows' plants (0 to 8 bytes; nine under `pytest-of-claygendron/`, one in a `tmp…` folder beside a test's `m.py`), one is a hard link (25 links) of a `.git/objects` file from a local clone, one sits inside an unpacked Docker disk image (July), and one is a 0-byte copy in a scratch copy of the package. None has a writer's size (6,148 bytes or more, born in place). In the same hours the checkout got them in nearly every folder of `build/`, as deep as 7 levels.

## R1, §4.8 — my ruling: within it; no owner question needed

§4.8 reads: "**Downloads are untrusted.** They unpack under `downloads/` and `build/`, never into the system, and execute only as build tools under the build's own control or as guests under wasmtime."

My reading:

- It governs two things: where an archive is **unpacked**, and how its code **executes**.
- After 097 and 066, a writable root under `T` holds (a) lxml's three `cwd_files`, copied by the host from the tree already unpacked under `build/` (`packages.py` `_files`, READ on `wave/08`), and (b) whatever the guest writes, matplotlib's `result_images/` included. Neither is an unpacking. Both are data read only by a guest under wasmtime, which §4.8 allows.
- `T` is not "the system" in §4.8's sense. The phrase guards against unpacking or installing into shared system locations. The repo's own gloss, "never the system's temporary folder (§4.8)" (`pins.py:112`, `tests/unit/conftest.py:15`), is about where tarballs are **extracted**, and it stays true: nothing is extracted there.
- There is a stronger precedent the spec should cite: **the product runner already does this on every call.** It copies the stdlib zip (CPython's and every package's members, from pinned downloads) and extracts matplotlib's data (members of matplotlib's tarball) into its private folder under `T` (`runner.py` `_zip_folder`, specs 017 and 023). The judge's `run-N/lib` and `mpl-data-N` under `GUEST_TMP` mirror exactly that.

So R1 is not a breach, and I see no need to ask the owner. If the owner wants it on record, one line in `decisions.md` settles it (Question 1, optional).

## Findings, most severe first

1. **Medium — the spec does not weigh the one variant spec 089's probe saw keep the writer out in place: `chflags hidden`.** The 089 memo's probe table (§1, "Variants") says a folder with `chflags hidden` got no `.DS_Store` inside it, and its size was not recorded in the parent's. Hidden flags never reach a WASI guest (filestat carries no flags, as it carries no mode, the reason 089's seal moves no fuel). A hidden `guest_workdir` would stay under `build/`, so R1, R2, R7, criterion 3 and the product-runner question would not arise. 089's options (§3) do not list it either, and 097's Decisions never mention it. §5.2 asks a specification to decide every choice. Relocation is still the stronger defence: it rests on the writer's scope (the home folder; two writers caught, both sizing it), which 089's 40-minute probe and the survey of `T` above support. The hidden flag rests on one row from one fresh folder, and nobody has shown that the Storage scan skips a hidden folder's descendants that change (a guest makes `/tmp/work` deep inside its root).

   Failure: the owner, or the build reviewer, asks why the judge's folders left `build/` (with a §4.8 reading, a fuel proof and a `TMPDIR` rule) when a one-flag fix exists. The spec has no answer in writing.

   Fix text (a new bullet in Decision 1): "**Why not `chflags hidden` in place.** Spec 089's probe saw one fresh hidden folder skipped (memo §1, Variants). That is one observation of one folder. It does not show that the writer skips a hidden folder's descendants when they change, and a guest's root changes deep inside on every run. Leaving the home folder rests on where both writers were seen to work, and on a temporary folder that has never held a writer's `.DS_Store` (the pre-build review's survey). So the folders move. The flag is not set, because it would add a second mechanism with no measured benefit outside the home folder." The builder may instead adopt the flag as well, on the unit suite's `work` folders (Decision 4's residual, which stays under the home folder). That is one `os.chflags(d, stat.UF_HIDDEN)` call on darwin, and it is optional.

2. **Low — the race row never reaches `update-index --force-remove`, so that change has no check that fails without it.** With the excludes in the add, `.DS_Store` is never staged, so `unstage_litter` finds nothing and the forced removal never runs. Both new script rows pass on the excludes alone. A later edit could revert the unstage to `git rm --cached`, and no row would notice.

   Failure: someone weakens or drops a pathspec line (a typo in `git_excludes`, or a new `OS_LITTER` name with a glob character), the add stages litter, the writer rewrites it, and the script fails again on `git rm --cached` with no row having caught the revert.

   Fix text (Decision 8, a third script row): "**`test_the_openblas_patch_script_unstages_litter_its_add_staged`** (the same layout). The wrapper drops `--pathspec-from-file=…` and `--pathspec-file-nul` from each `add`, so the add stages the planted `.DS_Store` files as if the excludes missed them. It rewrites them after the add. With `git rm -q --cached` in `unstage_litter` it fails with git's 'staged content different from both the file and the HEAD'; with `update-index --force-remove` the patches are made and name no litter. Its seen-failing line is taken on the branch's script with only the unstage reverted."

3. **Low — criterion 3's legs on main's code run under the home folder while the writer is active, so a leg can be voided.** That is the very failure the spec fixes. The criterion says a difference between two runs of the same code is noise, but says nothing about a void.

   Fix text (criterion 3, append): "A leg that ends in `HostLitter` measured nothing: it is run again, and the landing notes name it. Main's-code legs may instead run from a `git clone --local` of the branch's base outside the home folder (its guest folders are then under its own `build/harness`), which is what the comparison needs: the same code at two locations."

4. **Low — R2 is stated but not checked.** Criterion 3 proves location-freedom only where `T` and the checkout share a device (this Mac: `st_dev` 16777230 for both, EXECUTED in `tmpfacts.out`; GitHub's `macos-15`: INFERRED, both on the Data volume). On a host where they differ, the stages (under `build/harness`) and the run folders (under `GUEST_TMP`) would sit on two devices for the first time. A guest that compares `st_dev` across its grants could take another path.

   Fix text (Decision 8, the root check, on darwin): "and `os.stat(paths.GUEST_TMP).st_dev == os.stat(paths.HARNESS_TMP).st_dev`; otherwise it fails, naming both folders and their devices, and says to set `TMPDIR` to a folder on the checkout's volume outside the home folder: the fuel proof (criterion 3) covers one device only." The builder may answer in writing instead, if it judges the rule too strict for a checkout on an external disk.

5. **Note — the root check's order decides its seen-failing line.** On main, `paths.GUEST_TMP` does not exist. If the check reads it first, criterion 1's line on main is an `AttributeError`, not "a root under `build/harness`". It should test "not under the home folder" (comparing `realpath`s, since `HOME` may hold a link) before it names `GUEST_TMP`.

6. **Note — Decision 4's §4.8 clause is not a reason.** "Moving `work` would also move unit rows that unpack stand-in tarballs out of `build/`" — stand-ins are not downloads, and unit rows on `tmp_path` already unpack stand-ins in `T` (EXECUTED: `T/pytest-of-claygendron/pytest-2869/test_a_litter_name_the_tarball0/build/proj-1.2.3/`). The decision stands on its other reasons (millisecond runs, no fuel, a named `HostLitter`). Fix text: drop the sentence beginning "Moving `work` would also move".

7. **Note — the probe line and R5's version.** "This Mac: 2.51.0" is `/opt/homebrew/bin/git`. The OpenBLAS check runs `/usr/bin/git` (2.50.1, Apple Git-155). Say so; the unit rows' wrapper should exec the same git the check finds on its `PATH`.

8. **Note — leftovers and the disk.** A killed judge's folders now sit under `GUEST_TMP`, where `du build/` does not see them. The lane's disk check (memory: "df before accepts") should name `GUEST_TMP` too. The plugin's leftovers line (Decision 6) already names it. No spec change is needed; the lane may add one line to its checklist.

9. **Note — R-numbering.** R8 sits between R6 and R7. Renumber.

## The probe (item 5 of the brief)

EXECUTED, `probe3.sh` and `probe3.log`. Three identical trees shaped like a run's root and stdlib folder were changed every 5 s from 15:25:05 to 15:41:50:

- one under the home folder, at `~/Git/Repos/wasi_python-097-review-probe` (outside the repo, a sibling of the worktrees the writer has written into today);
- one in `T`, at `T/judge-097-review-probe`;
- one under `/private/tmp`, in my scratchpad.

**Result: no litter in any of the three** (0, 0, 0). So this probe is inconclusive too, like the spec's. The writer was active. It rewrote `~/.DS_Store`, `~/Git/.DS_Store`, `~/Git/Repos/.DS_Store`, the main tree's `.DS_Store` and its `.git/.DS_Store` at 15:33 to 15:34. `~/Git/Repos/.DS_Store` now holds `modD`, `ph1S` and `lg1S` records for the control tree's name (EXECUTED, read-only). So the writer **sized** the control from its parent, but in 17 minutes it never wrote inside it. Today's writer looks like Finder's windows (top levels, rewritten) rather than spec 089's Storage scan (a new tree's top within 7 s). The deep files in `build/` were born at 14:01 to 14:09, during the lane's rebuild.

What does settle something is the passive survey above. `T` has never held a writer-made `.DS_Store`, across months and 7,299 entries. The main tree holds 176 under `build/` alone (EXECUTED, `find`, 15:42). The claim "`T` is never written" is still INFERRED, but nothing contradicts it. The spec's own line ("the build repeats this probe while the writer is known to be active") should add a rule: **a probe counts only if its control under the home folder gets a `.DS_Store`.** Two probes have now failed that rule.

The control tree is left in place for the owner or the lane to remove (I may delete only inside my scratchpad): `~/Git/Repos/wasi_python-097-review-probe` and `T/judge-097-review-probe`.

## Simpler alternatives (item 6)

- **The whole checkout outside the home folder, as policy.** It works (the lane's stopgap clone under `/private/tmp` is doing it now), covers the stages, the unit suite and the OpenBLAS tree at once, and needs no code. But it binds every builder's worktree and the owner's own checkout, it cannot be enforced except by a check that refuses to run, and the system cleans `/private/tmp`. As a lane habit it is a good complement; as the fix it is weaker than 097.
- **Seal the writable roots differently.** No mode or ACL refuses `.DS_Store` by name; the guest writes as the same user, so any flag that stops the writer stops the guest too (`uchg`, 0555).
- **Filter litter from the watch or from `fd_readdir`.** Ruled out by 089 and by the owner (a quiet allowance), rightly.
- **`chflags hidden` in place.** Finding 1. Not tested enough to replace the move; the spec should say so.

## Verdict

**Build once finding 1 is answered in writing** (a context-only bullet in Decision 1; adopting the flag on the unit folders is optional). Findings 2 to 4 are Lows the builder takes as written or answers in writing; 5 to 9 are notes. R1 is within §4.8 as I read it, and needs no owner answer.

## Questions only the owner can answer

1. *(Optional, not blocking.)* §4.8: do you read "never into the system" as allowing a guest's writable root in the per-user temporary folder to hold copies of a few tarball members (lxml's test documents) that only a guest reads, as the product runner already does with the stdlib zip and matplotlib's data? I read it as allowed.

One line: 097's split is right and the runner accepts the new folders; weigh `chflags hidden` in writing, add a row that reaches the forced unstage, and build.
