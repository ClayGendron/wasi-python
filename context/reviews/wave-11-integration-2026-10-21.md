# Review of wave 11's integration (101, 102, 112, 114, 113)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of 101, 102, 112, 113 or 114 and
  reviewed none of them before; their pre-build, build and re-reviews were other agents'. It is the
  wave's integration reviewer (AGENTS.md rule 8; constitution §5.7).
- **Reviewed:** the wave's tip **`11ce98a0`** (`wave/11`), linear on main `1875d4cd`: 101 and 102
  stacked (`..861d5e4b`), then 112 (`..599a99f9`), then 114 (`..33f22580`), then 113
  (`..11ce98a0`); no merge commit.
- **Run:** none of my own (the brief: no dispatch). The local read is the lane's full judge on the
  tip, `build/wave-11/judge1.log` in the main tree, read in section 3. The three-system read is the
  wave's dry run after the acceptance (section 5).
- **Ran** (in this worktree, on `review/wave-11` at `11ce98a0`, no artifact set; nothing while
  `build/lane.lock` existed but single node ids): `ruff check src tests` → "All checks passed!";
  `ruff format --check src tests` → "163 files already formatted"; by node id, the wave's
  cross-entry rules (`test_no_string_names_a_context_document`,
  `test_release_shards_cover_the_judge`, `test_release_judges_in_shards`,
  `test_the_set_key_names_every_build_input`, `test_the_release_reuses_a_set_only_on_a_branch`,
  `test_the_reuse_decision_refuses_tags_and_main[*]`) → **12 passed**; the structural rules
  (`test_src_type_checks_under_mypy_strict`, `test_no_function_is_over_eighty_lines`,
  `test_no_module_under_src_is_over_the_line_ceiling`,
  `test_no_mutable_is_bound_at_module_level_outside_the_process`,
  `test_only_the_engine_seam_touches_wasmtimes_private_api`, `test_the_platform_is_chosen_once`,
  `test_src_names_no_context_document`, `test_code_outside_src_names_no_context_document`) and
  `tests/unit/test_runner_package.py` → **12 passed**; the rebase comparisons of section 1;
  `sameness.py` over the lane's record (section 3).
- **Box:** 60 minutes, waiting for the lane's judge included: 15:14 to 15:40 (the judge ran 15:14 to 15:34).

## 1. Interactions no entry's review could see

### 1a. Each rebase, the code lines (EXECUTED)

The lane range-diffed every rebase. I re-checked the two runner entries the other way: the `+`
and `-` lines of each entry's reviewed diff, against its base, compared with those of its rebased
diff against the new base (`git diff <base> <tip> -- src tests recipes scripts [README.md] | grep
'^[+-][^+-]'`, then `cmp`):

| entry | reviewed | rebased | result |
|---|---|---|---|
| 113 | `1875d4cd..21cc7296` (its build review's confirmation) | `33f22580..881a4b1b` | identical, 788 lines; the commits after `881a4b1b` touch no code (`git diff --stat 881a4b1b 11ce98a0 -- src tests recipes scripts .github release` empty) |
| 114 | `1875d4cd..2147b335` (its build review) | `599a99f9..a94a7474` | identical, 403 lines; nothing after `a94a7474` touches code |
| 101+102 | re-review on `a66d9659` | `861d5e4b` | `a66d9659..861d5e4b` is one `context/` file |
| 112 | build review's fix `ab296e9e` | `8a92d836` | `ab296e9e..8a92d836` is the three named strings: release.yml lines 178 and 512 (both zero-patch steps, now the same name), the kit step of the four judge jobs, and `scan.ZERO_PATCH_STEP` |

No workflow line under `.github/` still cites a specification (`grep -E 'spec [0-9]{3}'` on both
workflows: none).

### 1b. 113 and 114 in the runner (READ, `git diff 1875d4cd 11ce98a0 -- src`)

They meet in `_call.py`, `_sessions.py` and `runner.py`, on different lines, and the merged code
keeps each one's order.

- **The order of the walk.** In both `_run_checked` and `_open_session` the sequence is: 113's
  `_engines._caches(cache)` (host-side: `$WASI_PYTHON_CACHE` and the platform defaults from the
  *host's* `Path.home()`); `_places._walk_grants(..., others=...)`, which judges every grant and
  root against every cache and only then makes a missing root; the preopens listed from that
  walk; then 114's `_guest_home`, which appends the empty HOME, if any, after the grants and
  before the mounts. 113's `others=` adds rows to the judge's `runtime` and `missing` lists only;
  it adds no preopen, so 114's numbering argument (its pre-build M1, Decision 6) is unchanged.
- **The placeholder HOME against the cache rules.** None. The guest's HOME (`/tmp/.home-<hex>`)
  is a guest variable; 113 reads only the host's environment and `pwd`, so no cache is computed
  from the guest's HOME, and `env=` cannot steer one. The empty HOME's host folder is a
  `_Private("wasi-python-")` in the system temporary folder, made 0700 and read-only to the guest,
  after the judge and outside it (`walk(..., judge=False)`), as the session's scratch folder
  always was. It cannot be a way into a cache: it is read-only, fresh per call, and no grant may
  be at or above the temporary folder (`_shared_folders`). Its name cannot meet a cache's: the
  defaults end in `wasi_python` (underscore), the private folders begin `wasi-python-`.
- **Cleanup.** A call releases the store, then `_release_home` (the fresh HOME's budgeted
  removal, or the empty one's walk closed, then its folder removed). A session's
  `_release_session` keeps its order with `_call._release_home` in place of the old
  `_remove_home`. The empty HOME's walk is not in `state.walked` (that list is taken before
  `_guest_home` appends), so `_release_home` is its one closer; a second close is a no-op. 113
  touches none of this.
- **Tests.** 113's builder ran 114's three HOME rows and 113's thirty-six rows on the merged tree
  (329 passed, its notes); 114's three new functions are in `test_v1_2_hostile_guest.py`, which
  101's plan runs whole in `own-hostile` on three systems; 113's unit file is in `own-runner`
  (`release_shards.toml`, line 126), and `test_release_shards_cover_the_judge` passes on the tip.
- **The upstream suites.** They run through the judge's own driver (`tests/harness/guest.py`,
  wasmtime-py directly, `ENV = {"TMPDIR": "/tmp", "HOME": "/tmp"}`), not through the runner. So
  neither runner change reaches a normal or a release-tier upstream group; 114 reaches them only
  by its two zip members and the rebuilt snapshot.

### 1c. 112 against 101 and 102 (EXECUTED)

The semantic conflict 112's rebase named is real and closed: 101's reuse rule (R3, R4) pairs the
build and build-shard zero-patch steps by `ZERO_PATCH_STEP`, and 102's shard rule (rule 3)
compares judge-release's steps with the judge jobs' text for text; rewording one side alone turns
each red. With the three strings reworded both sides agree: the six rows above pass by node id.
No other 101 or 102 string cites a document (112's string rule passes). 112's `plugin.py` hunk
kept 102's `--tier` and `--accept-tier-move` as built.

### 1d. 101's set key against 112 and 114

The key reads every tracked file under `scripts/` and `recipes/`. 112 changes two `scripts/`
files and 114 adds `recipes/reportlab_start_up_stand_in.py` and changes `70_zip.sh`, so the
wave's key differs from every key the cache holds: the first branch dispatch after the landing
builds from source (a miss), as it should. `test_the_set_key_names_every_build_input` passes on
the tip, so the key's inputs and the tree agree.

### 1e. 102's gather against 113's and 114's rows

The gather collects both tiers (`gather.COLLECT_ARGV`, 102's H1 fix). 114's fifteen rows are
normal-tier checks in a file every system's `own-hostile` runs, so every record carries them and
G3 has nothing to say. 113's thirty-six rows are unit rows: they count in each record's unit
suite, not in the goal checks G3 compares. Neither entry adds a release-tier row, a release group,
or a shard. What neither entry's run could show: the gather on a run with all five entries, since
every 102 run's gather was skipped behind its red growth leg, and 113's and 114's runs had no
release tier. That read is the dry run's (section 5).

## 2. The combined claim list

From each entry's "For the lane" (as built, and the rebase paragraphs). 101, 102 and 112 give
TOML blocks; 113 and 114 give prose, turned into blocks here. The file, parsed by
`sameness.load_claims`, is
`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/6c490d24-fe1d-441f-9d11-d529e2f0c242/scratchpad/claims/wave-11.toml`;
its text is in Appendix A, for the lane to copy to `build/wave-11/lane/claims.toml`.

| | 101 | 102 | 112 | 114 | 113 |
|---|---|---|---|---|---|
| **new rows** (normal tier, gained) | 9: `test_the_set_key_names_every_build_input`, `test_the_release_reuses_a_set_only_on_a_branch`, and `test_the_reuse_decision_refuses_tags_and_main[*]`'s seven cases | none in the normal tier; 21 release-tier rows, deselected (`numpy-slow-*`, `pandas-slow-*`, `cpython-release-*`, `contourpy-slow-rest`, two classes) | 1: `test_no_string_names_a_context_document` | 15: `test_a_planted_reportlab_start_up_file_never_runs[*]` (8), `test_reportlab_start_up_hooks_are_the_zips_empty_modules[*]` (2), `test_where_the_runner_makes_no_fresh_home_the_home_is_empty_and_read_only[*]` (5) | none (its rows are units) |
| **units** | 58 | **113** (its block says 112; L1) | 14 | 0 (one unit test changed, `test_a_writer_cannot_keep_a_home_removal_going`) | 36 (`tests/unit/test_runner_module_caches.py`) |
| **changed checks** | none (rules widened, no node id) | contourpy's normal groups (`filled-*`, `lines-*`) | none (a unit id renamed) | 9 rows: `test_nothing_is_writable_by_default[plain\|snapshot]`, `test_no_root_and_no_grants_runs`, `test_a_mount_at_the_root[plain\|snapshot]`, `test_a_mount_at_tmp_means_no_home` (same id), `test_seaborn_takes_its_scipy_paths[plain\|snapshot]`, `test_scikit_learn_says_what_it_lacks` | none |
| **tier moves** | none | 17 contourpy groups to the release tier | none | none | none |
| **growth** | none | `cpython-fs`, `-a`, `-b`, `-c` (the driver's `Z` line), `contourpy-1`, `contourpy-rest` (`-m 'not slow'`): slow rows | none (`MANIFEST`'s two recipe lines; no byte row) | the zip +1,289, the snapshot +6,371 (the bytes rows), and fuel both ways on guest rows by the rebuilt snapshot, plus +7,433 per start without a fresh HOME | none |
| **retired** | none | none (five plot *shards* leave the matrix; no check) | none | none (the mount-at-`/tmp` check kept its id) | none |
| **judge files** | `release_shards.toml`, `shards.py`, `gather.py`, `sameness.py`, `scan.py`, `test_rules.py`, five unit files | `tiers.py`, `upstream.py`, `packages.py`, `regrtest.py`, the driver, `plugin.py`, `scoreboard.py`, `shards.py`, `gather.py`, `sameness.py`, the four TOMLs, CPython's release lists, `known_gaps.toml` (+12, its two classes), two `expected/` files, unit files | `scan.py`, `test_rules.py`, `pyproject.toml`'s marker and 22 more files' strings | four check files, `test_runner_sweep.py` | `test_runner_module_caches.py`, one `release_shards.toml` line |

**Totals.** Gained 25 (9 + 1 + 15); units **+221** (58 + 113 + 14 + 36); moved 17; retired 0;
absent 0; deselected 38 (the 17 moved and the 21 new release-tier rows). Nothing is counted
twice: 102's release-tier rows are not "gained" in a normal record (deselected, reason `release
tier`); 113's rows are units only; the one shard file both 101 and 102 rewrote is one
judge-changed file.

**The unit count, by file** (EXECUTED: `pytest --collect-only -q tests/unit` here at `11ce98a0`,
2,244 rows, and in a `git clone --shared` at `1875d4cd`, 2,023; +221): `test_set_key.py` +40,
`test_tiers.py` +47, `test_runner_module_caches.py` +36, `test_scan.py` +33 (112's 14, 101's 3,
102's 16), `test_gather.py` +25 (101's 7, 102's 18), `test_scoreboard.py` +13, `test_shards.py`
+13 (101's 5, 102's 8), `test_sameness.py` +8 (101's 3, 102's 5), `test_plugin.py` +5,
`test_packages.py` +1. 101's 58, 112's 14 and 113's 36 are exact, so 102's is the 113 left, one
more than its block: the re-review's L4 row (`gather.COLLECT_ARGV`) came after L1 set 112 (L1
below).

## 3. The lane's judge on the tip (EXECUTED: read `build/wave-11/judge1.log` and its record)

`uv run pytest -n 3` in the main tree on `11ce98a0`, the set rebuilt from the pins
(`build/wave-11/build.log`: python.wasm 99,421,513 `d41926055c3f8697`, unchanged; the snapshot
104,517,748; the zip 53,915,154), 19 min 51 s, no `--accept`. Its last lines:

```
wasi_python v1: 810/935 pass · 85 gap · 2 blocked · 0 fail · 38 deselected   (unit suite 2249/2251, 2 skipped)
  v1.1 47/48 blocked 1 · v1.2 175/176 blocked 1 · v1.3 233/356 gap 85 · v1.4 231/231 · v1.5 52/52 · rules 72/72
ratchet vs 8115549282: lost 0 · absent 0 · unrun 0 · gained 25 · grew 100 · moved 17 · judge changed: pyproject.toml, tests/checks/test_rules.py, tests/checks/test_v1_2_hostile_guest.py and 60 more
RED: 100 metric(s) grew; 17 check(s) moved between tiers (say --accept-tier-move)
=========== 3059 passed, 4 skipped, 85 xfailed in 1191.66s (0:19:51) ===========
```

Against wave 10's acceptance (802/889, unit suite 2,028/2,030): pass 802 + 25 − 17 = **810**;
rows 889 + 25 + 21 = **935**; units 2,030 + 221 = **2,251**; fail 0, gap 85, blocked 2 (the
three systems and the wheel, as before).

**Every red line, explained.**

| red line | count | explained by |
|---|---|---|
| `MOVED` | 17 | 102's seventeen contourpy groups (its claim, `--accept-tier-move`) |
| `GREW` bytes | 2 | 114: `test_binary_is_a_core_wasm_module[snapshot]` 104,511,377 → 104,517,748 (+6,371) and `test_stdlib_zip_is_bytecode_only_and_deflated` 53,913,865 → 53,915,154 (+1,289), the figures 114's notes give |
| `GREW` fuel, guest rows | 89 | 114's rebuilt snapshot and placeholder HOME, in the eleven check files of its claim (hostile-guest 20, embedding 19, zips-directory 11, default-profile 9, matplotlib 7, lxml 5, regex 5, data-stack 4, artifact-set 3, portable 3, scipy 3); the largest +0.31% (`test_recursion_through_python_raises[min-key-snapshot]`), as 114's notes and its build review's L2 say; 146 metrics fell the same way, upstream groups included |
| `GREW` fuel, upstream groups | 9 | `contourpy-1` +0.35%, `contourpy-rest` +1.8e-4, `cpython-a` +1.4e-4, `cpython-b` +1.9e-4: **102's** claim; `matplotlib-render-2a` +3.5e-4, `matplotlib-render-2b` +3.9e-4, `matplotlib-rest-b2` +7.1e-4, `mpl-mplot3d` +4.5e-4, `pillow` +1.02e-4: **no claim names them (M1)** |

(98 fuel rows past 1e-4 by my own comparison of the record with `accepted.json`'s darwin
metrics, plus the two bytes rows: 100.) **No pass count moved anywhere** (no `passes` line in
sameness), and no fail.

**The known expectations.**
- `test_manifest_recipes_match_the_tree` **passes** (lost 0): the rebuilt set carries 112's two
  script hashes and 114's recipe line.
- **113's thirty-six rows run and pass**: `test_runner_module_caches.py` is in the record's
  collected files, and the unit suite is 2,249 passed of 2,251, the 2 skipped the base's own
  (wave 10's acceptance: 2,028/2,030, 2 skipped).
- **114's fifteen new rows pass**: they are 15 of the 25 gained (with 101's nine and 112's one),
  and the v1.2 area is 175/176 (wave 10's 160/161, +15).
- **102's growth** is partly not seen: `cpython-fs` is −2.4e-4 and `cpython-c` −5.9e-5 against
  the acceptance, where 102 alone measured +6.9e-4 and +1.8e-4. Net of 114's zip they fall; a
  claim not seen is only a note.

**Sameness with the claims** (EXECUTED: `uv run python tests/harness/sameness.py --claims
<Appendix A> build/wave-10/lane/accepted-record.json <the lane's record>`, the record copied
from `build/progress/latest.json` at 15:34):
- with the five blocks as the entries wrote them (102 at 112 units, 114 naming no upstream
  group, no unit file named): **exit 1**, 27 upstream lines (26 groups' fuel, both directions,
  from `matplotlib-axes` −0.103% to `matplotlib-rest-b2` +0.071%, and `numpy-core`'s
  `string-comparisons` fuel fact +0.12%), the suite line (2,030 → 2,251 against 220 claimed), and
  three `collected_files` lines (`test_set_key.py`, `test_tiers.py`,
  `test_runner_module_caches.py`);
- with Appendix A: **exit 0**, `note: explained by claims: 101 11 · 102 8 · 112 2 · 113 2 · 114
  209`, `release-tier rows not compared: 38`, and "claimed, not seen" notes only (102's release
  rows, 102's `filled-*` and `cpython-c`, 114's nine changed rows, whose change is in source).

**Why M1's rows are 114's (INFERRED).** python.wasm is byte for byte main's. The upstream groups
run on the judge's own driver, not the runner (section 1b), so neither runner change reaches
them. 102 changes the argv of contourpy's groups and the CPython driver only, and its survey
measured numpy's and pandas' normal groups equal to the instruction on its set. What every group
reads that changed is the zip, two members longer, whose directory each start builds; the
movement in both directions is the same heap-layout shift 114's build review measured on the
guest rows (120 up, 110 down). No pass count moved, so it is growth, not behaviour.

## 4. The flags

The lane composes one string per flag, "Wave 11 (…) on <acceptance commit> …: " followed by each
entry's reason, as in wave 10. Each entry's reason, as it should be pasted:

- `--accept`:
  - `101: a branch dispatch reuses a set the cache holds under its commit's key, checked, matched by two rebuilds and a third fresh build, the gather needing same-bytes; a tag or main always builds; the build shard on a fresh arm64 Linux build every run; own-hostile and own-embedding-a split out on macOS; nine new rules rows; the artifact set does not change`
  - `102: the release tier: slow tests run before a publication, nothing left out; numpy's and pandas' slow cases, contourpy's slow and random_big cases, CPython's cpu-gated tests and four inline-cpu modules in full, in 36 release groups, 8.36 T on d0d91cef; the normal tier sheds about 4 T` (its own, unchanged)
  - 112's, 113's and 114's own `--accept` strings, unchanged (112 and 113 in their *For the lane, as built*; 114 `114: HOME is never the root`).
- `--accept-judge`: 101's, 102's and 112's strings as in their blocks; 113's with "thirty-six"
  (its *as built*); 114's `114: the guest always has a HOME; checks that encoded none now read
  the empty read-only one`. 63 judge files changed (the ratchet's line), the union of section 2's lists.
- `--accept-growth`: 102's string unchanged, then 114's with M1's clause:
  `114: the zip gains reportlab's two empty hooks (+1,289 bytes), so the snapshot is rebuilt over it (+6,371 bytes) and a program's own work moves a little either way (the largest guest row +0.31%); a call without a fresh HOME carries one more preopen and variable (+7,433 on -c pass); and on darwin every upstream group's fuel moves both ways with the zip's two new members, python.wasm byte for byte main's, every pass count unchanged (matplotlib-rest-b2 +7.1e-4 the largest rise, matplotlib-axes -0.10% the largest fall; the integration review's M1)`
- `--accept-tier-move "102: contourpy's slow and random_big cases move to the release tier, seventeen groups (the owner, 2026-10-20)"`
- `--retire`: **none**. No accepted check is absent.

The acceptance should then show what section 3 shows with the red lines gone: 810/935 pass, 0
fail, lost 0, absent 0, unrun 0, gained 25, grew 0, moved 0, and `release tier not run` on the
ratchet line for the seventeen moved rows (102's *For the lane*: the lane's message quotes it).

## 5. For the lane after landing

**Before the fast-forward** (each entry's text names it the lane's; none is in the tree at
`11ce98a0`, EXECUTED `grep`): 102's constitution amendment (§5.5's release rule and §5.7's
"normal tier", with its header line) and its AGENTS.md text for rules 3a and 6b; 101's sentence
for rule 3a, if the lane takes it; 101's L6, the two roadmap lines (the macOS exit tail; a run's
width, about 38 jobs); 102's block appended to `context/release-tier-claims.toml`, which is
still empty; 112's CHANGELOG line, proposed in its *For the lane, as built* and not written
(L3).

**The dry run (step 7).** Dispatch it on **`wave/11` at the acceptance commit**, as the progress
README's step 7 says, not on `main` (M2). On it:
- `inputs` says `tier=normal`; `judge-release` is **skipped**; the gather **runs and concludes
  success**, `meta.tier` `normal`. That is 102's criterion 5 and the first half of criterion 7,
  which no 102 run has shown yet: runs 5 to 9 each skipped the gather behind their red growth
  leg. A gather skipped or red on a run whose legs are all green is a finding against 102.
- three systems, every job green. After the acceptance no growth is left to be red; any red
  line must be a GREW line (CI's macOS fuel against the lane's darwin record at 1e-4) or G7;
  anything else, above all on Windows, where 113's and 114's runner code first meet, is fixed
  forward before the next wave.
- the set: the key misses (section 1d), so `meta.set_source` is `built`, and the three
  rebuilds' `SHA256SUMS` hash to the lane's **`1556bbd5`**; else G7 names it.
- the wheel: about 98.27 MB (wave 10's 98,259,192 plus a few kilobytes, INFERRED), still under
  the owner's 100,000,000-byte line; the run's `rebuild-wheel` jobs give the figure.

**After the fast-forward:** the push to main starts `set-cache.yml` for the first time; record
its run id, whether `seed` built, and the entry's size (101's criterion 7); the first branch
dispatch on main's key shows `cached 'true'` and `Cache restored` (101's L5).

**At the release acceptance** (102's, before the tag): it is the first, so there is no previous
release record to compare with; the release-tier rows are read on a zip and a driver neither
102's survey nor its criterion 3 ran together (L4).

## Constitution checks

- **§4.1:** no patch added or changed; 114's change to reportlab is a recipe
  (`recipes/reportlab_start_up_stand_in.py`, packed by `70_zip.sh`), as the rule asks first.
- **§4.2:** `downloads/SHA256SUMS` untouched by the wave.
- **§4.3 to §4.5:** `tests/public_api.txt` untouched; python.wasm byte for byte main's, so no
  guest import or export moves; the zip and snapshot move by 114's two members only.
- **Rule 4:** `tests/known_gaps.toml` (+12), `tests/upstream/*.toml`, `tests/upstream/expected/`
  (two class files) and CPython's lists (`tests/upstream/python/`, thirteen release lists) change
  only in 102's commits (`git log 1875d4cd..11ce98a0 -- tests/known_gaps.toml tests/upstream`:
  `bcaae57a`), each as its survey's measured groups, classes and gaps, a judge change with its
  reason and reviewed (102's build review and re-review); `context/progress/` only its README
  (101, 102). No expectation was edited to turn a run green.
- **Structure** (113 and 114 together): `mypy --strict`, the 80-line rule, the ceiling, the
  module-level mutable rule, the engine-seam rule, the one-platform rule and both citation rules
  pass on the tip; `_platform.py` 1,464 lines and `_call.py` 1,343, both under 1,500. Neither
  entry is structural by its Kind line, and their union adds no module, mutable, seam or
  platform branch.
- **§7:** nothing tripped; no `--accept`, push or artifact in git by any entry.

## Findings, most severe first

1. **M1 (Medium, against 114's claim list): no claim names the upstream groups 114's zip moves.**
   (114, *For the lane, as built*, "grown".) On darwin, 26 upstream groups' fuel moves past 1e-4
   in both directions and `numpy-core`'s string-comparisons fact by +0.12%; five of them are
   `GREW` lines of the lane's judge (`matplotlib-render-2a`, `-2b`, `matplotlib-rest-b2`,
   `mpl-mplot3d`, `pillow`), every pass count unchanged (section 3). **Failure:** sameness with
   the entries' claims exits 1 on 27 upstream lines, which rule 6a reads as an ejection of 114 for
   its own mechanism, and `--accept-growth` without a reason for them accepts growth no one
   stated (wave 09's and wave 10's M1, the same shape). **Fix (context only, done here):**
   Appendix A's 114 block (`test_upstream_suite[*` under `grows`) and the clause in 114's
   `--accept-growth` (section 4). Then sameness exits 0 (EXECUTED).
2. **M2 (Medium, the lane): "the dry run on main" cannot show the gather succeed.** A dispatch on
   main is a release run whatever its inputs (102, Decision 12; `release.yml` line 102), so it
   runs the twelve release legs for the first time and its gather is red at G7, "a tag (or a
   dispatch on main), and the newest acceptance did not run the release tier"
   (`gather.py:384-387`), until a release acceptance exists. A normal landing acceptance never
   makes one. **Failure:** read as the wave's check, that run's red gather is either taken for a
   defect or waved through as "G7", and criterion 5's normal-run gather is still never seen.
   **Fix:** step 7 on `wave/11` at the acceptance commit (the progress README's own step), read
   as section 5 says; the dispatch on main belongs to the tag's rehearsal, after the release
   acceptance.
3. **L1 (Low): 102's `units` is 113, not 112.** (102, *For the lane*, the claim block, and Landing
   notes item 13's "L1 `units = 112`".) The per-file count of section 2 leaves 113 for 102; the
   re-review's L4 added the `COLLECT_ARGV` row after L1 had set 112. **Failure:** the suite line
   is unexplained in sameness (2,030 → 2,251 against 220). **Fix:** Appendix A says 113; the lane
   may write the one number into 102's notes.
4. **L2 (Low): three new unit files are named by no claim.** `tests/unit/test_set_key.py` (101),
   `tests/unit/test_tiers.py` (102), `tests/unit/test_runner_module_caches.py` (113).
   **Failure:** three `collected_files … only in the second record` lines in sameness. **Fix:**
   each in its entry's `new` list, as wave 10 named 045's unit file; done in Appendix A.
5. **L3 (Low, the lane): the landing edits the entries leave to the lane are not yet in the
   tree.** 112's CHANGELOG line; 102's constitution and AGENTS.md text; 102's ledger block; 101's
   L6 roadmap lines (section 5). **Failure:** a landing without them leaves the constitution
   saying "the full judge" at §5.7 while the judge now has two tiers, and the ledger empty for
   the release acceptance. **Fix:** the landing commit, before the fast-forward.
6. **L4 (Low): no ledger line for 114, which moves every release-tier group's inputs.** 114
   changes the zip all release groups read, after 102's survey and baseline (criterion 3, on
   `d0d91cef`). Release-tier rows are not compared at a landing, and the first release
   acceptance has no previous record, so nothing is hidden now. **Fix (context only):** with
   102's block, a one-line 114 block in `context/release-tier-claims.toml` ("the zip's two
   members move every release-tier group's fuel both ways; passes unchanged") so the release
   acceptance reads a stated reason rather than a surprise.
7. **Note: 114's rebase paragraph counts 27 rows**, "all 27 of the new and changed rows and their
   guards"; its build review's L1 settled 15 new and 9 changed (24), and the rest are guards.
   Nothing to change.
8. **Note: the CHANGELOG's 114 and 113 bullets have no blank line between them**, where every
   other entry has one. Cosmetic; the lane may add it with 112's line.

## Disposition (for the lane; the entries' builders where named)

1. M1: Appendix A and the clause in section 4; read the acceptance's upstream rows against it: a
   group whose **passes** move is a finding against 114, not covered.
2. M2: step 7 dispatched on `wave/11`; its run id and gather conclusion in the acceptance notes.
3. L1, L2: Appendix A; 102's number in its notes at the lane's choice.
4. L3, L4: the landing commit.
5. Notes 7 and 8: no action beyond what they say.

## Verdict

**Lands as merged at `11ce98a0` once** the lane's acceptance on that tip:
1. runs with the flags of section 4 (M1's clause in 114's `--accept-growth`, 102's
   `--accept-tier-move`, no `--retire`) after the landing edits of L3;
2. shows 810/935 pass, 0 fail, lost 0, absent 0, unrun 0, gained 25, and moves and grows only
   what section 3 lists (17 moves; 100 grown rows; no pass count moved);
3. prints, from `sameness.py --claims` with Appendix A, nothing but notes (EXECUTED on the lane's
   judge record: exit 0);
4. and the step-7 dry run, on `wave/11`, reads three systems green with the gather concluding
   success beside a skipped `judge-release` (M2).

Every rebase is its reviewed diff plus the named hunks: 113's and 114's code lines byte for byte,
112's three strings closing the one real semantic conflict in 101's and 102's rules. 113 and 114
share three runner files and no decision: the walk judges every cache before 114's empty HOME is
listed, and that HOME is guest-side, read-only and outside every cache. No entry is ejected.

One line: the faster run, the release tier, the string rule and both security fixes merge
cleanly; the only gap is in the paperwork, 114's zip moving upstream fuel that no claim named,
and the dry run belongs on `wave/11`, where 102's gather can finally be seen to pass.

## Appendix A: the claim file

Copy to `build/wave-11/lane/claims.toml` (EXECUTED with `sameness.py` above: exit 0).

```toml
# Wave 11's claim list (101, 102, 112, 114, 113), for
#   uv run python tests/harness/sameness.py --claims <this file> \
#     build/wave-10/lane/accepted-record.json <the lane's wave-11 record>
# Written by wave 11's integration reviewer from each specification's "For the lane" (as built).
# 101, 102 and 112 are their TOML blocks as written; 113 and 114 give prose, turned into blocks
# here. 113's thirty-six rows are unit rows (tests/unit), so they are units, not new checks.

[[claim]]
spec = "101"
new = [
  "tests/checks/test_rules.py::test_the_set_key_names_every_build_input",
  "tests/checks/test_rules.py::test_the_release_reuses_a_set_only_on_a_branch",
  "tests/checks/test_rules.py::test_the_reuse_decision_refuses_tags_and_main*",
  "tests/unit/test_set_key.py",
]
units = 58

[[claim]]
spec = "102"
new = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[numpy-slow-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[pandas-slow-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-release-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-slow-rest]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[pandas-slow-b-no-threads]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_class[cpython-release-a-stdlib-zip-error]",
  "tests/unit/test_tiers.py",
]
changed = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-filled-*",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-lines-*",
]
grows = [
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-fs]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-a]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-b]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-c]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-1]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[contourpy-rest]",
]
growth = "102: the regrtest driver's Z line moves every CPython group's fuel; contourpy's normal groups run -m 'not slow'"
units = 113  # 112 in its block; the re-review's L4 row (COLLECT_ARGV) makes 113, counted per file

[[claim]]
spec = "112"
new = ["tests/checks/test_rules.py::test_no_string_names_a_context_document"]
units = 14

[[claim]]
spec = "114"
new = [
  "tests/checks/test_v1_2_hostile_guest.py::test_a_planted_reportlab_start_up_file_never_runs[*",
  "tests/checks/test_v1_2_hostile_guest.py::test_reportlab_start_up_hooks_are_the_zips_empty_modules[*",
  "tests/checks/test_v1_2_hostile_guest.py::test_where_the_runner_makes_no_fresh_home_the_home_is_empty_and_read_only[*",
]
changed = [
  "tests/checks/test_v1_2_hostile_guest.py::test_nothing_is_writable_by_default[*",
  "tests/checks/test_v1_4_embedding.py::test_no_root_and_no_grants_runs",
  "tests/checks/test_v1_4_embedding.py::test_a_mount_at_the_root[*",
  "tests/checks/test_v1_4_embedding.py::test_a_mount_at_tmp_means_no_home",
  "tests/checks/test_v1_3_default_profile.py::test_seaborn_takes_its_scipy_paths[*",
  "tests/checks/test_v1_3_default_profile.py::test_scikit_learn_says_what_it_lacks",
]
grows = [
  "tests/checks/test_v1_1_artifact_set.py",
  "tests/checks/test_v1_2_hostile_guest.py",
  "tests/checks/test_v1_2_portable_and_sealed.py",
  "tests/checks/test_v1_3_data_stack.py",
  "tests/checks/test_v1_3_default_profile.py",
  "tests/checks/test_v1_3_lxml.py",
  "tests/checks/test_v1_3_matplotlib.py",
  "tests/checks/test_v1_3_regex.py",
  "tests/checks/test_v1_3_scipy.py",
  "tests/checks/test_v1_3_the_zips_directory.py",
  "tests/checks/test_v1_4_embedding.py",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[*",  # the integration review's M1
]
growth = "114: the zip gains reportlab's two empty hooks, the snapshot is rebuilt over it; a call without a fresh HOME carries one more preopen and variable; on darwin every upstream group's fuel moves both ways with the zip's two new members (python.wasm unchanged), every pass count unchanged"
units = 0

[[claim]]
spec = "113"
new = ["tests/unit/test_runner_module_caches.py"]
units = 36
```


## The lane's addendum (2026-10-21)

- **The conditions met.** The acceptance on `25983899` (the landing edits on `11ce98a0` and this
  review) ran with M1's clause in 114's `--accept-growth`: history line 93, 810/935 pass, 0 fail,
  85 gap, 2 blocked, lost 0; sameness against wave 10's record with Appendix A's claims exits 0.
  The acceptance commit `da665abe`; the lane's handoff `6411d4d5` (context only); main
  fast-forwarded `1875d4cd..6411d4d5`.
- **M2.** The step-7 dry run is 39667712127 on `wave/11` at `da665abe`. Attempt 1 failed only at
  "Download the pinned inputs" (`curl: (22) … 504` from freetype's pinned Savannah URL, the host
  down from about 20:10 to 20:25 UTC); attempt 2, the failed jobs re-run with nothing changed,
  is green on three systems. `inputs` said `tier=normal`, `judge-release` skipped, the gather ran
  and concluded success (102's criterion 5 and the first half of 7); the set `1556bbd5` on every
  host; 805/935 on CI, 7 blocked; the wheel 98,264,488 bytes.
- **L1 to L4** are in the landing edits `25983899`: 102's block in the ledger with `units = 113`,
  the three unit files in Appendix A's `new` lists, 112's CHANGELOG line, 102's constitution and
  AGENTS.md text, 101's roadmap lines, and 114's one-line ledger block. That block carries the
  growth reason alone, without Appendix A's wildcard `grows` for 114: in the ledger it would
  excuse every release-tier group's fuel at the release acceptance, which is wider than M1's
  landing-time reason.
- **Note 8** written in by the lane with this addendum: the blank line between the CHANGELOG's
  114 and 113 bullets.
- **101's criterion 7.** The fast-forward's push started `set-cache.yml`'s first run, 39684360599
  on `6411d4d5`: the key `wasi-python-set-v1-28075ae2…` missed in main's cache, `seed` built the
  set from the pins on arm64 Linux (22:09 to 22:28 UTC, one fetch from Savannah after its outage)
  and saved it, 90,718,147 bytes, the same key the wave's dry run had cached on `wave/11`. The
  push of these landing notes is the next run (context only, so the same key): the first hit.
