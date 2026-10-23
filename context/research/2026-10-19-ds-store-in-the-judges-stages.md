# `.DS_Store` in the judge's stages: who writes them, where they matter, and how the judge stops caring

- **Status:** draft, 2026-10-19. Asked for by the owner ("This .DS_Store issue keeps popping up … develop a solution so we don't have this again"), then narrowed by the owner: "I am less concerned with the process that makes the DS store files, more that our builds shouldn't be affected by them." So the writer is identified only as far as the first hour's evidence went; the rest is immunity. The judge change is spec 089 (the stage seal and the grant watch); the build's half is spec
  090. Spec 089 lands before 083 (the lane's order, with the owner's agreement).
- **Owner:** Clay Gendron
- **Researcher:** a research agent (Claude Opus 5.5), in two scratch clones outside every git tree; the main tree's `build/` was only read. Evidence beside this memo, in `2026-10-19-ds-store-in-the-judges-stages/`: `tools/` (the record decoder, the simulated writer, the trial script), `trials/` (each trial's outcome lines and writer log; r3's and r4's records), `probe-*.txt`, and `prototype.diff` (against `d84bb7e`, which carried 083). Log lines and `lsof` samples from the owner's system are quoted here only, not kept.
- **Follows:** `context/research/2026-10-17-finder-litter-breaks-a-desktop-build.md` (spec 018: the build's side) and spec 083's build review, whose last addendum found `.DS_Store` files in the CPython stage mid-run (`083-buildreview/lane/watch.out`).

Labels: **EXECUTED** (run here), **READ** (read in code, logs or files), **INFERRED** (reasoned).

## Short version

- **What writes them:** macOS's folder-size cache. Every `.DS_Store` under `build/` today holds only four record types, `lg1S`, `ph1S`, `moDD`, `modD`: a subfolder's logical size, physical size and dates. None holds a view setting. They are written by DesktopServices when something sizes a folder. Two processes were caught sizing this checkout: **System Settings' Storage pane** (its `StorageManagementService`, re-sizing "Documents" on every file change under the home folder), and **Finder** (walking every child of `~/Git/Repos`). Which of the two wrote the stage's files was not settled; `sudo fs_usage -w -f filesys | grep DS_Store` would settle it in a minute.
- **Why it moves fuel:** the guest is granted `build/harness/cpython/run-*` at `/cpython`. A file that appears there mid-run changes what the guest lists and the folder's times. EXECUTED here: a simulated writer on a scratch clone's stage turns `cpython-archives`' clean **164,648,434,127** into **164,609,014,815** (−2.4e-4, past the 1e-4 tolerance), and the check still **passes**. That is the silent drift spec 083's review saw.
- **The fix:** the judge seals every read-only stage (no write bit on any folder in it, so no process of the user's can add a file) and watches every guest run (litter in any grant, any change in a read-only grant fails the run, naming the file; a litter name handed to the guest by `fd_readdir` too, once 083's listing hook exists). It never filters a file out of the guest's view. EXECUTED: with the prototype, the same writer is refused on every folder and the fuel is the clean value (numbers in "The prototype").
- **The build side:** the build already skips three litter names (spec 018). Widen the set to AppleDouble `._*`, `Icon\r` and the volume-root names; make the release tarball pack exactly `SHA256SUMS`' files; let the two artifact-folder checks ignore litter names only. A real stray source file still fails every check that catches one today.
- **Today:** there is no safe mitigation outside the judge. A symlinked `build/harness` outside the home folder was tried and **refuted** (§6). So 089 lands first, and the lane runs a tripwire beside its serial judges until it does.

## 1. What writes the files

**The records (EXECUTED, `tools/dsrecords.py`).** All 101 `.DS_Store` files under the main tree's `build/` were decoded: 3,985 `moDD`, 3,989 `modD`, 3,987 `ph1S`, 3,986 `lg1S`, nothing else. The key of each record is a subfolder's name: `build/tools/.DS_Store` holds the sizes of `python` and `wasi-sdk-33.0-arm64-macos`; `clone/.git/.DS_Store` the size of `objects`. So these are not Finder's window settings (`icvp`, `lsvp`, `bwsp`, `vSrn`, which `~/.DS_Store` does hold). They are a folder-size cache, written when something asks DesktopServices for a folder's size. Each carries the `com.apple.FinderInfo` invisible flag and nothing that names its writer.

**The scanners (EXECUTED).**

- `StorageManagementService` (pid 2959, started 2026-10-18 20:14) runs under System Settings' Storage pane (`Storage.appex`, up two days; System Settings up four). Its log says, about 3,700 times in 20 minutes: "Updating Documents size due to change to the following paths", listing paths in `wasi_python/build/…` and `wasi_python-086/build/…`. `lsof` caught it holding folders open deep in the main tree (`build/tools/wasi-sdk-33.0-arm64-macos/share/wasi-sysroot/include/ wasm32-wasi/eh/c++/v1/__cxx03`, `build/reviews-evidence`, `context/prior_art/cpython`) and in `build/harness/guest-m0gndg21`: the trees where `.DS_Store` files reappeared that nobody opened. The binary links `DesktopServicesPriv`, the framework that writes `.DS_Store` (`otool -L`).
- Finder (pid 1296) was seen opening every child of `~/Git/Repos` in turn (`lsof`, 1,500 samples), and has five windows on screen, one of them Get-Info-sized (CoreGraphics window list; names are hidden without Screen Recording permission). `~/Git/Repos/.DS_Store` sets the Size column on, "calculate all sizes" off.

**A probe (EXECUTED, `probe-watch-final.txt`).** A small tree made under the home folder got a `.DS_Store` at its top 7 s after it was made, and one more level each time a file changed below (`plain/`, `x.noindex/`, `build/`), each 4 to 7 s after the Storage scan logged the change. The same tree under the scratch folder (`/private/tmp/…`) never got one in 40 minutes. Variants:

| folder | got a `.DS_Store` inside it? | its size recorded in the parent's? |
|---|---|---|
| plain | yes | yes |
| `x.noindex` | yes: `.noindex` stops Spotlight, not this | yes |
| a dot-folder (`.dotdir`, `build/.harness`) | not seen in the probe; but `.git/` folders in the main tree have them | yes, once its parent was sized |
| `chflags hidden` | no | no |
| mode 0555 | **no** | yes |
| `chflags uchg` | **no** | yes |

So neither a `.noindex` name nor a dot-name keeps the files out (option (a) of the brief is rejected). A folder without its write bit does: the writer runs as the user and respects the mode.

**Timing (READ, `083-buildreview/lane/watch.out`, `stat`).** After the lane deleted every `.DS_Store` under `build/` at about 15:06:35, ten reappeared within the same second (15:06:40), spread over unrelated trees and `.git/` folders, and about 100 within two minutes. INFERRED: the writer keeps the cache in memory and writes it back when it sees the file go. Deleting them does not help; it triggers a burst.

**Worktrees.** `wasi_python-086` (building) got three, all shallow (`.`, `build/`, `build/Python-3.15.0/`); `wasi_python-083` and `-087` none in the same 20 minutes. The main tree got 105, as deep as 12 levels. INFERRED: depth follows where caches already existed and what was sized; the main tree has been shown in Finder for weeks.

**Not settled, and dropped at the owner's word:** which of the two processes wrote the stage's two files on 14:41:46. A 45 ms `lsof` loop (3,000 passes) never caught a `.DS_Store` open: the write takes microseconds. `sudo fs_usage -w -f filesys | grep -i ds_store` would name it.

## 2. Where a stray file can reach a verdict or a metric

**The judge's grants (READ, `tests/harness/`).** Every guest run is `guest.run`: a fresh writable root `build/harness/guest-*/run-N/root` at `/`, the stdlib's own folder at `/usr/local/lib` (read-only), matplotlib's data (`mpl-data-N`, read-only, shared by a session's runs) and any extra grants:

| grant | host folder | lifetime | a stray file there |
|---|---|---|---|
| `/cpython` (065's groups) | `build/harness/cpython/run-*` | one judge run, five groups | **moves fuel; the review saw it** |
| `/upstream` (numpy, pandas) | `build/harness/upstream/run-*` | one judge run | moves fuel ("pytest lists its root folder", `upstream.py:771`) |
| `/` | `guest-*/run-N/root` | one guest run, writable | moves fuel if the guest lists it |
| `/usr/local/lib` | `guest-*/run-N/lib` | one guest run | moves fuel if the guest lists it |
| `…/matplotlib/mpl-data` | `guest-*/mpl-data-N` | one session | small: matplotlib reads by name |
| other checks' grants | `tmp_path`, check folders | one check | rare: fresh, short-lived |

A file appearing mid-run moves fuel two ways: the guest lists it (an extra entry, and its own inode count from spec 083), and the folder's `mtim`/`ctim` move, so spec 083's `FileFacts` stamps the folder with the clock's next value, shifting every later clock read. The second needs no listing at all, so filtering names from `fd_readdir` would not be enough (INFERRED from `FileFacts.stamp`).

**Caches.** `zips-*-v2` is the only harness folder reused across runs; it is read by name only. Every stage is a fresh `mkdtemp`, so litter never carries from one run to the next. (READ, survey.)

**The build (READ, a survey of `scripts/`, `release/`, the workflow).** Spec 018 already skips `OS_LITTER = {".DS_Store", "Thumbs.db", "desktop.ini"}` (`scripts/litter.py`, held equal to `tests/harness/paths.OS_LITTER` by a unit check) in the zip walk, the licence collection and the artifact list. Gaps:

| place | today | with litter |
|---|---|---|
| `make_stdlib_zip.py` walk (`SKIP_NAMES`) | skips the three | `._x`, `Icon\r` become zip members; `._x.py` fails to compile (loud) |
| `assemble_artifacts.py` `drop_litter`, `listed_files`, `licence_files` | skips the three | `._x` hashed into `SHA256SUMS`, packed into a licence text |
| `release/version.py:162` `write_assets` (rglob of `build/artifacts`) | **no filter** | `.DS_Store` packed into the release tarball |
| wheel (`cp -R build/artifacts`, hatchling) | hatchling drops `.DS_Store` only | `._x`, `Icon\r`, `Thumbs.db` enter the wheel |
| judge `sums_errors`, `wheel_errors` (`tests/harness/artifacts.py`) | no filter, by design | a loud failure (README's documented case) |
| `pins._patched_drift` (spec 020) | skips names the tarball lacks | litter is ignored; a real extra file in a *build tree* is not seen at all (scoreboard: "files a build adds inside a source tree", not machine-checked) |
| step 90's untracked check, `paths.dirty_path` | git's ignores | `.DS_Store` is ignored only through the owner's `~/.gitignore_global`; on another Mac it stops step 90 |
| CPython stage | written from the tarball's members | immune to litter in `build/Python-*/`; `left_out` lists it as a fact |
| upstream stage | copies only tarball and patch names | immune; `left_out` lists it |

## 3. The options weighed

- **(a) A stage folder Finder skips** (`.harness`, `*.noindex`): rejected. EXECUTED: `.noindex` folders get `.DS_Store`; `.git/` folders in the main tree have them.
- **(b) Check each stage after each group**: kept, widened. Alone it turns silent drift into a loud failure, but on this Mac today it would fail nearly every run (the review's four main-tree runs were all polluted). It is the detector, not the defence.
- **(c) Seal the stage**: kept, as the defence. EXECUTED: a 0555 folder refuses the real writer (the probe) and the simulated one (the trial). Folder modes are not visible to a WASI guest (filestat carries no mode; spec 083 answers the times), so fuel cannot move; the trial confirms it. Removal must unseal first: today's `shutil.rmtree(…, ignore_errors=True)` would leave a sealed stage behind silently.
- **(d) A lane tripwire** (`find` before and after): kept as today's mitigation, and as a lane step until the judge change lands.
- **(e) System settings**: there is no switch that stops local `.DS_Store` writes (`DSDontWriteNetworkStores` and `DSDontWriteUSBStores` cover network and USB volumes only). Closing System Settings' Storage pane stops the Storage scan; closing Finder windows on the checkout stops Finder's. A recommendation only, since the judge must hold either way.
- **Moving every harness folder out of the home folder**: works on this Mac (EXECUTED: the probe; the reviewer's clones), but depends on which folders today's writers happen to scan, and puts stage contents (tarball members) outside `build/`. A mitigation, not the fix.
- **Filtering litter out of `fd_readdir`**: rejected. It hides a file from the guest, misses the folder-time channel, and is exactly the kind of quiet allowance the owner ruled out.

## 4. The prototype (EXECUTED, `trials/`)

Two scratch clones of main `d84bb7e` (`git clone --local`), each with an APFS clone of the CPython tarball and tree and of the frozen set `s-c50ca51fae5eb55b-c9dcb5b8` (`shasum -c` OK). The prototype is `tests/harness/litter.py` (new), small edits to `guest.py`, `regrtest.py`, `upstream.py` and `tests/checks/conftest.py`, and `tests/unit/test_host_litter.py` (14 rows, green; `ruff check` and `ruff format --check` green). The whole diff is `prototype.diff` beside this memo. A prototype-only switch `P_LITTER=off|watch|on` picks the defences. The simulated writer (`tools/writer.py`) writes a 6,148-byte `.DS_Store` into every folder of every `run-*` stage, every 0.3 s, as the user. Each trial is one `cpython-archives` run by its node id, serial, `-p no:cacheprovider`, its record in the scratch folder.

| trial | defences | writer | outcome | fuel |
|---|---|---|---|---|
| base | none (main's code) | no | pass | **164,648,434,127** (the reviewed value) |
| r3 | off | yes: 173 of 173 folders written, from 0.3 s into staging | **pass** | 164,609,014,815 (−2.4e-4) |
| r2b | on | no | pass | **164,648,434,127** |
| r4 | on | yes: 172 files written in the 2 s of staging (removed by `seal`), then 173 of 173 folders refused on every pass for 5 min 20 s | pass | **164,648,434,127** |
| r5 | watch only | yes | **fail** after 18 s: `HostLitter: … /cpython/.DS_Store (before the run); …` | not recorded |
| r6 | off; `build/harness` a symlink to a folder elsewhere | no | pass | **164,648,434,127** |

So: without the defences the writer moves fuel and the check passes (r3); with the seal the writer is refused and the fuel is the clean value to the instruction (r4); with the watch alone the run fails at once, naming the file (r5); and neither the seal nor a symlinked harness folder moves a clean run's fuel (r2b, r6). Seven grant-heavy fast checks also pass with the prototype at their accepted fuel (`test_matplotlib_data_is_granted_read_only` ×2, `test_a_trailing_slash_symlink_rename_cannot_escape` ×2, `test_grants_reach_the_guest_in_any_order[plain]`, `test_home_follows_a_writable_tmp_grant[a root]`, `test_the_command_grants_folders`; `-n 3`: 7/7, grew 0, lost 0), and leave no folder under `build/harness` without its write bit.

One more finding: r3's stage, removed by today's `shutil.rmtree(…, ignore_errors=True)` while the writer ran, was **left behind** (`run-56d5heaw`, with a `.DS_Store` in each of five folders): the writer refilled folders between rmtree's unlinks, spec 018's "Directory not empty" on the harness side, silenced by `ignore_errors`. The prototype's `remove` retries (as spec 018's `remove.sh` does); r5's stage, removed with the writer still running, was gone.

(The first `on` run, r2, failed with "`/usr/local/lib/python315.zip` vanished during the run": the watch looked after the driver released the run's stdlib copy. Fixed by watching first; r2b is that fix.)

## 5. Recommendations

1. **The judge change, spec 089:** seal read-only stages, unseal and retry at removal, and watch every guest run's grants (litter before or after; any change in a read-only grant). It lands before 083; the `fd_readdir` watch follows with 083's rebase or a later spec.
2. **The build's half, spec 090:** one widened litter definition shared by the judge and the build; the release tarball packs its list, not its folder; artifact-folder checks ignore litter names only; the repo's own `.gitignore` lists litter. Every place that compares a tree with a list still fails on a stray file that is not litter.
3. **The owner's Mac, when they are back:** close System Settings (its Storage pane has been open two days and re-sizes the home folder on every file change); close Finder windows and Get Info panels on `~/Git/Repos` or the checkout. Optionally run `sudo fs_usage -w -f filesys | grep -i ds_store` for a minute during a build to name the writer for the record. Nothing else: there is no setting that stops local `.DS_Store` writes, and the judge must not need one.

## 6. For the lane, until 089 lands

**Refuted: the symlinked harness.** The draft proposed pointing `build/harness` at a folder under `/private/tmp` through a symlink, for 083's serial rerun. The lane tried it: **87 runner and session checks failed**, because the product runner refuses any root that passes through a link in a user-writable folder (READ, the lane's run). Trial r6 ran one CPython group through the judge's own driver, which never meets that rule, so it could not show it. Do not use it.

**What holds today:**
- Do not delete `.DS_Store` files before a run. Fresh stages do not need it, and deleting makes the writer rewrite a burst of them.
- Run the reviewer's watcher beside every serial judge on the main tree: `083-buildreview/lane/watch.sh build/harness <log> <stop>` lists any `.DS_Store` or `._*` newer than `<stop>.start`, twice a second, until `<stop>` exists. A path under `cpython/run-*`, `upstream/run-*` or `guest-*` voids the run; say so in the landing notes. Expect most runs on this Mac to be void while System Settings' Storage pane is open: the review's four main-tree runs were all polluted.
- If the owner is back, closing System Settings and Finder windows or Get Info panels on `~/Git/Repos` stops the writers for the run.
- Once 089 lands, the seal refuses the writer and the watch names anything that gets through, so the tripwire is no longer needed.

One line: macOS's folder-size cache writes `.DS_Store` into any folder under the home folder that something sizes, including the judge's live stages; seal the stages and void any run whose grants change, so a stray file can be refused or named, never measured.
