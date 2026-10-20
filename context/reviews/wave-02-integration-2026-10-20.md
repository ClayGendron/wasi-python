# Review of wave 02 — integration of 039, 041, 073 and 093

- **Date:** 2026-10-20 (UTC; 2026-10-19 local)
- **Reviewer:** a fresh agent that wrote and reviewed none of the four entries
- **Reviewed:** `wave/02` at `170b4e2`: main `e8ba20a`, then 039 (`2d0a583`), 041 (`1ef8256`),
  073 (`f077cf0`) and 093 (`170b4e2`). 092 is not in the wave.
- **Time box:** 45 minutes (the wave holds three build-class entries).
- **Run:** none of my own. The lane rebuilt the set in the main tree at `f077cf0`. 093 changes
  nothing under `recipes/`, `scripts/`, `src/`, `downloads/` or the workflow
  (`git diff --name-only f077cf0 170b4e2` on those paths is empty, EXECUTED), so that set is the
  tip's set.
- **Re-ran:** eight single node ids, in a `git archive 170b4e2` export in my scratchpad with its
  own `build/` and no artifact set, started before `build/lane.lock` appeared (02:58Z): 8 passed,
  5.25 s (`nodes.log`). They were `test_rules.py`'s `test_carried_patches_follow_the_rules`,
  `test_known_gaps_are_well_formed`, `test_specifications_have_their_header_and_sections`,
  `test_specifications_have_no_open_question`, `test_release_shards_cover_the_judge` and
  `test_every_package_names_its_own_suite`, and `test_build_scripts.py`'s
  `test_main_puts_entry_points_beside_metadata_or_stops` and
  `test_an_sdists_entry_points_go_beside_its_metadata`. The run's ratchet line names the judge as
  changed in 38 files, which is exactly `git diff --name-only e8ba20a 170b4e2 -- tests/`
  (`judge-files.txt`). No pytest ran after the lock appeared.

Each item is labelled EXECUTED, READ or INFERRED.

## Acceptance criteria against evidence

### 1. Each entry's `git range-diff` against its reviewed tip

Files beside this one: `rd-039.txt`, `rd-041.txt`, `rd-073.txt`, `rd-093.txt` (EXECUTED).

- **039** (`9d89535..dcd94ff` against `e8ba20a..2d0a583`). Two commits are `!`, five `=`, and
  `2d0a583` is new and touches `context/` only.
  - The build commit (`84c97c8`): every difference is a context line that wave 01 changed. These
    are the README's patch count 7 → 8 (087), `assemble_artifacts.py`'s `MODIFIED` line (087), the
    embedding check file's neighbour (084), and the `known_gaps.toml` neighbour (078 removed the
    trap gaps). No line of 039's own moved.
  - `18fba2d` (the old rebase note): a CHANGELOG context line only.
  - This matches the note's "no conflict; seven shared files merged and read".
  - **A second check (EXECUTED):** I compared the changed lines (`+` and `-`) of each entry's
    build-class paths before and after the rebase: `recipes/`, `scripts/`, `src/`,
    `.github/` and `downloads/`. For 039 they are byte-identical. For its `tests/` files, all are
    identical except `known_gaps.toml`, which differs by one blank line only.
- **041** (`dcd94ff..1e012ed` against `2d0a583..1ef8256`). Only the build commit is `!`. It shows
  exactly the two named hunks:
  - the README's results row, 8 → **10** (old 7 → 9);
  - the `known_gaps.toml` region.

  `b6cb284` and `50acd67` are `=`, and `1ef8256` is new and touches `context/` only. The changed
  lines of `recipes/`, `scripts/`, `.github/`, `downloads/` and `tests/` are byte-identical before
  and after (EXECUTED).
- **073** (`a6dfc17..84c3df5` against `1ef8256..f077cf0`). Two commits are `!`, the build commit
  and B1's, by the named hunks alone:
  - `known_gaps.toml`: wave/02's file less 073's ten lines;
  - the README's *Measured* rows: the snapshot `-c pass` row keeps 039's tier A clause, and the
    plain row is 039's;
  - the CHANGELOG: both sides kept.

  Eight commits are `=`, and `f077cf0` touches `context/` only. The changed lines of
  `recipes/reactor_bootstrap.py`, `recipes/reactor_main.c`, `test_v1_3_data_stack.py` and
  `test_v1_4_embedding.py` are byte-identical before and after. `known_gaps.toml` differs by the
  trailing blank line only (EXECUTED).
- **093** (`97be88a..0a9d48b` against `f077cf0..170b4e2`). One commit is `!`, the check commit,
  by its CHANGELOG hunk alone: the entry now follows 084's bullet, with no blank line after it.
  The check's hunk is identical. The other five commits are `=`. 093 has no rebase-note commit;
  the coordinator's message names the six commits, and there was no conflict to name.
- **Nothing changed that a builder did not name.**

### 2. The named hunks keep their meaning (READ)

- **041's patch count.** `recipes/patches/` on the tip holds ten `.patch` files: kiwisolver 1,
  libxml2 1, matplotlib 1, networkx 1, numpy 2, pandas 1, pillow 1, regex 2. The README's row says
  10, which is 087's 8 plus 041's 2. `test_carried_patches_follow_the_rules` passes (each patch
  has its draft under `context/upstream/patches/`, its CHANGELOG line and its rules).
- **The release's tree count.** `release.yml` says "All twenty-two trees" and greps
  `^22 passed`. `tests/harness/pins.py`'s `SOURCE_PATTERNS` has 22 keys: main's 19, plus 039's
  pyyaml and markupsafe, plus 041's networkx (EXECUTED). 087 patched an existing tree, so it added
  none.
- **073's README rows.** The snapshot row reads "43.8M guest instructions (15.6M before spec 073);
  with tier A in the zip, 20.4M without spec 073 (spec 039) and about 28M more with it". This is
  honest: no measured chain number exists yet, and the note says the wave run's number is the
  set's own. The plain row is 039's 218M, and 073's +72,583 lies below its precision.
- **093's CHANGELOG position** is cosmetic. The 0.1.0a8 section already mixes bullets with and
  without blank lines between them.

### 3. `tests/known_gaps.toml` on the tip (EXECUTED)

`git diff e8ba20a 170b4e2 -- tests/known_gaps.toml` removes exactly:
- 073's `test_run_keeps_an_unclosed_files_bytes[snapshot]` entry with its three-line comment;
- the file's trailing blank line.

Nothing else is removed or added. Along the chain:
- **078's nine `c-stack-*` trap gaps** are already gone on main `e8ba20a` (zero matches). None
  comes back at any step.
- **039 adds four gaps** at `2d0a583`: `test_pandas_styler_renders_from_the_zip[plain]`,
  `test_networkx_atlas_reads_from_the_zip[plain]`, and
  `test_upstream_class[pandas-frame-styler-templates]` and `[pandas-io-formats-styler-templates]`.
- **041 removes those same four** at `1ef8256`.
- **073 removes only its own entry** at `f077cf0`.
- **093 does not touch the file.**

The two `styler-templates` lists exist on the tip and are empty. Their `[[expected]]` classes stay,
emptied, as 041's F5 notes. `test_known_gaps_are_well_formed` passes.

**Verdict: exactly right.**

### 4. 041's answers to its build review (`1e012ed`, now `50acd67`), unconfirmed until now (READ; the rows EXECUTED)

- **F1 is met.** `packages.toml`'s networkx reason reads "pinned as its sdist since spec 041,
  which carries its tests; staging and running them is spec 067's". `kind = "later"` and the
  closer are kept. It is named in 041's `--accept-judge`.
- **F2 is met.**
  - `check_entry_points(names: Iterable[str], …)` takes `entries` (the members gathered), and
    `origins` is gone.
  - The new `main()` case holds both mutants the review named. Deleting the guard from `main`
    fails its first half: with no `--metadata`, `main` must stop. Moving the guard before the
    `--metadata` loop fails its second half: with `x/../x/PKG-INFO`, `main` must write both
    members.
  - Both rows pass on the tip.
  - Its assertion `"x/PKG-INFO" in line` would fail on Windows, where `str(Path)` uses `\`. But
    `test_build_scripts.py` is in no files shard, so it runs in `rest`, which runs on macOS and
    Linux only (`release_shards.toml`'s header). This is not a defect today (N3).
- **F3** concerned the builder's worktree set. The lane rebuilds from empty, so it is moot.
- **F4** (the layout reason) is in the `--accept-growth` text.

### 5. 039's F1 and F2 answers (`0a64145`, now `e75d7c5`), which its build review did not re-review (READ)

- **F1:** the README line about `hasattr` and `getmembers` raising `TemplateNotFound` was written
  in, and 041 then closed the gap and removed it. No `TemplateNotFound` line is left in the tip's
  README, which is right once 041 lands in the same acceptance.
- **F2:** `pandas.toml` on the tip re-selects the eleven Styler files. Its comment says so, and
  no `[[not_selected]]` entry for them remains. 041's claim list expects `pandas-frame` 10,853
  and `pandas-io-formats` 1,972.

### 6. The claim lists: overlaps and the attribution rule

**New checks** come from 039 (jobs, default-profile checks, unit rows), 041 (its job, the two
snapshot rows, `networkx`'s source tree, two unit rows) and 073 (eight v1.4 rows). No name is
shared. 093 adds none.

**Gaps that close:** 039's four, through 041 (net zero against main), and 073's (h). No entry
retires anything.

**Passes:** none fall. `pandas-frame` goes 10,852 → 10,853 and `pandas-io-formats` 977 → 1,972,
so no `--accept-fewer-passes` is needed with 041 in the acceptance.

**Judge files:** 38 in all. Files shared between entries:
- `known_gaps.toml`: 039, 041 and 073;
- `test_v1_3_data_stack.py`: 039 and 073;
- `test_v1_4_embedding.py`: 039 and 073;
- `test_v1_3_default_profile.py`, `jobs.py`, `needs.py`, `pins.py`, `pandas.toml`,
  `packages.toml`, `test_artifact_rules.py`, `test_build_scripts.py`: 039 and 041.

Each shared hunk was read. They do not overlap in meaning.

**Growth: the rule the lane uses.** Let Δ be a row's metric on the tip minus its value in
`accepted.json` at `47b3695`. The claims add up as follows. 039's numbers come from its own
records (its build review's `latest-full-reviewer.json`), so they are measured, not inferred.

| row kind | expected Δ, and whose |
|---|---|
| `test_binary_is_a_core_wasm_module[plain]` (41,099,863) | **+≈2.3 K, 073 alone**. 039 and 041 leave `python.wasm` unchanged. 073 measured +2,268 on its own base. |
| `test_binary_is_a_core_wasm_module[snapshot]` (44,634,185) | **+≈0.73 MB**: 039 +729,607 (45,363,590 on its record), 041 −3,308, 073 a few K either way. |
| a plain `run` row that reads no metadata | **about +49 M to +58 M**: 039's start +50.6 M (+45.6 M on the hard-exit row), 073 −1.4 M to +7.3 M, 041 within ±0.05 %. |
| a snapshot `run` row that finalizes, reading no metadata | **about +30 M to +80 M**: 039's +4.7 M, 073's unfreeze +28 M to +70 M (a few M more is INFERRED, from tier A's 2,014 members in the frozen heap), 041 within ±0.45 %. A few snapshot rows rise less (lxml's encoding workaround: +7.4 M from 073 and +2.07 M from 041). |
| a snapshot row that skips finalization (`os._exit`: `test_unbuffered_output_survives_a_hard_exit[snapshot]`, 1,213,059) | **≈ 0** (+1,623 from 041; 039's record shows 1,212,377, so no start cost). A +28 M move here would contradict 073's mechanism. |
| a session row | 039's measured start cost. 073 says sessions are unchanged, since they already unfreeze at close (055). |
| a row that reads distribution metadata | 039: +205 M a scan (+199 M in CPython's groups). |
| 035's member-walking checks, and the GB18030 check (bs4 and html5lib) | 039. |
| upstream groups (pandas and numpy) | 039 +0.10 % to +0.33 % (one to three scans a session); 041 −0.09 % to +0.11 % (stage), plus **`pandas-io-formats` +22.8 G** and **`pandas-frame` +0.69 G**; 073 +0.01 % to +0.27 % (each snapshot run's unfreeze). |
| CPython's five groups | 039 +0.13 % to +4.27 % (`cpython-fs` largest, twelve scans counted), plus 073's unfreeze per snapshot run. |
| `test_upstream_suite[numpy-core]` (155,796,744,081 without the 84 cases) | **a small residual only**: 039's scans and 073's unfreeze, which is +0.19 G by 073's review. **Not** 073's +4.48 G layout clause: see M1. |
| `fuel_facts.string-comparisons` (a fact, not ratcheted; 091 quoted 59,054,444,847) | 091 asks that a move of more than 10 % (outside 53.1 G to 65.0 G) get one sentence of cause from the reviewer. |

**A row no claim covers** is any of these:
- a plain row grown by more than about +58 M that is not one of the named exceptions above
  (metadata, member walks, GB18030, the regex timeout rows' start);
- a snapshot `run` row grown by more than about +80 M with no metadata read;
- any growth on a row that skips finalization;
- `python.wasm` moving by more than a few K;
- an upstream group outside the percentages above;
- numpy-core's own fuel growing by more than about +0.5 % (about +0.8 G).

On paper, I found **no existing row that falls outside every claim**. The regex timeout rows
(087's `test_a_timeout_past_2_147_seconds_fires`, 921,030,897 plain and 648,507,790 snapshot)
are covered explicitly by 039's claim. They also take 073's share by the snapshot rule.

## Findings, most severe first

### M1 (Medium, lane): 073's `--accept-growth` still carries the numpy-core layout clause that spec 091 retired

- **What (READ).** 073's restated flag (its "Rebased onto wave/02" section) ends with "and
  numpy-core by a link-layout term in the bool-keyed type lookup of test_string_comparisons … of
  either sign on a new binary (+4.48 G on its own base)".
- 091 landed in wave 01. Since then, numpy-core's metric runs without `test_string_comparisons`'
  84 cases, and their fuel is the fact `string-comparisons`. 091's Decision 10 says, by name:
  "**073.** … After 091 the lane rewrites that clause to the residual its rebase measures, and
  the fact's value." Its Intent adds: "the notes quote the fact in one clause and drop the
  numpy-core layout clause from the growth reason".
- 073's rebase note never mentions 091. So the flag as written would cover a multi-G numpy-core
  rise that no longer has that cause. That is the very thing 091 exists to stop.
- **Fix (the lane, in the accept text, no rebuild):**
  - Replace the clause with "numpy-core's own fuel by its snapshot runs' unfreeze, +<the measured
    residual> (091 holds the layout term as the fact string-comparisons, <value>)".
  - If numpy-core's metric grows by more than about +0.5 %, it needs a cause before acceptance.
  - If the fact sits outside 53.1 G to 65.0 G, I owe one sentence (091's 10 % band) when I see
    the log.

### M2 (Medium, owner or lane): 073 has no release-workflow run, which AGENTS.md rule 2 asks of a build-class entry before "built"

- **What (READ).** Rule 2: "A build-class, growth or Windows-touching specification is 'built'
  only once its builder has dispatched the release workflow on its branch and every red line
  there is a growth line or G7; the build review reads that run." 073's own "For the lane" says:
  "Not yet read: this branch has no CI run (the wave's entry criterion 2…)".
  - 039 had dry run 39264473516. Its two failures were fixed in `afade05`.
  - 041's dry run 39345809724 ran on 039's tip, so it covers 039's fixes, and was red only for
    growth.
  - 073 has had **no Linux or Windows judge at all**.
- **Why it matters here.** Three of 073's new checks run on Windows in `own-embedding`:
  - A keeps an unclosed file in every mode;
  - C checks the native `__main__`;
  - E compares `-m` and directory error messages with native ones.

  E is the kind that differs by host. Step 7's dry run comes *after* main moves, so a Windows
  failure would be fixed forward, as 093 itself was for 078.
- **Fix, one of these:**
  - (a) Push `wave/02` and dispatch the release workflow on `170b4e2` now, while the lane
    judges. Before step 6, check that every red line is growth (against `47b3695`'s accepted
    state) or G7.
  - (b) The owner waives it for this wave in writing.
  - If (a) shows a non-growth red line in one of 073's rows, eject 073. 093 replays onto
    `1ef8256` with no conflict: its only shared file is the CHANGELOG (INFERRED).

### L1 (Low, README): the prose still says "eight carried patches"

- **What (EXECUTED).** README line 56: "The platform's facts, documented rather than patched (with
  eight carried patches, below and under *matplotlib in the guest*, *lxml in the guest* and *regex
  in the guest*)". The results row says 10.
- This is inherited: 041's reviewed tip `1e012ed` already said "seven" when its row said 9, and
  its build review missed it.
- **Fix:** "ten carried patches", and name where pandas' and networkx's are described (the
  default profile's section). Do it in a README-only commit. Rule 6b lets README-only commits
  follow a dry run. It need not hold the landing.

### N1 (note, lane): copy the build reviews before step 2

- The tip's `context/reviews/` holds 039's and 041's pre-build reviews and 093's build review.
  It does not hold:
  - 039's build review (it is in `59150da`, which is not an ancestor of `170b4e2`, and in
    `039-buildreview/`);
  - 041's build review (`041-buildreview/`);
  - 073's spec and build reviews, with the delta look as an addendum (`073-review/`).
- Copy them in step 2's commit, as wave 01 did, and cite this review.
  `test_landed_specifications_cite_an_existing_review` will look for them once the landing notes
  say "landed".

### N2 (note, lane): the flags, joined

The wave-01 review's L1 still holds: each accept flag keeps only its last value. So pass one
quoted string per flag, joining the entries' texts in wave order:
- `--accept`: "Wave 02: 039, 041, 073, 093 …", with 093's text inside it;
- `--accept-judge`: 039's, 041's, 073's and 093's texts, in that order;
- `--accept-growth`: 039's, 041's, and 073's text as rewritten for M1.

There is no `--accept-fewer-passes` and no `--retire`.

### N3 (note): 041's `main()` row is Windows-unsafe if it is ever sharded there

- It asserts `"x/PKG-INFO" in line`, but the message carries `str(Path(...))`. If
  `test_build_scripts.py` ever moves into a three-system files shard, assert on
  `str(Path("x/PKG-INFO"))` instead, as the older row does.

### N4 (note, step 3a): comparison records

- **073:** no reviewer full record exists on its rebuilt set. Its sameness rows compare against
  the builder's `latest-full3.json`, as its note says.
- **093:** its review is a build review with mutants. Check that it left a `-n 3` record.
- **Me:** I keep no local `-n 3` record. No set built from the wave's recipes existed outside the
  lane's tree, and the lock now forbids a tier.
- So under step 3a the wave may be "not counted". That never blocks a landing.

## Constitution checks

- **§4.1 (patches).** 041's two patches each have:
  - a file under `recipes/patches/`;
  - a draft under `context/upstream/patches/`;
  - a facts sheet (`context/upstream/5-…`, `6-…`);
  - a CHANGELOG line.

  `test_carried_patches_follow_the_rules` passes. The MANIFEST hash is the lane's build's.
  `git status` is clean under `recipes/`, `scripts/` and `downloads/SHA256SUMS` in the main
  tree, and 093 changes none of them (EXECUTED). So the MANIFEST's `recipe` lines will match
  CI's, as in wave 01.
- **§5.6.** 041's answer commit (criterion 4) and 039's F1 and F2 answers (criterion 5) are now
  reviewed. Neither reopens a finding. 073's B1 to B4 were confirmed by its build review's delta
  look ("Lands").
- **§5.7.** One integration branch, four entries, three of them build-class: within the six
  allowed.
- **§7.** No check, golden, allowance or `context/progress/` file is edited to turn anything
  green. 073 restates check (b)'s `START_FACTOR` from 8 to 3, by the owner's answer to question
  103. That is a judge change with a reason, and it is in the judge-hash line. On the chain it
  still has margin: about 218 M against about 48.5 M, roughly 4.5 (INFERRED).

## Accept log: pending

The lane holds `build/lane.lock` (from 02:58Z). I check its GREW list against the table in
criterion 6 when the lane sends it.

## Verdict

**Lands as merged at `170b4e2`**, on three conditions:
1. **M1:** 073's numpy-core clause is rewritten to the measured residual and the fact's value.
2. **M2:** 073's missing release run is either read before step 6 (every red line is growth or
   G7) or waived by the owner. If that run shows a non-growth red line in 073's rows, eject 073.
3. **The accept log's GREW rows** each fall inside the criterion 6 table.

L1 and N1 to N4 need no action to land.

One line: the four entries merged with only their named hunks, and their build inputs are
byte-identical to the reviewed tips; the gaps, patch count and tree count are exactly right; fix
073's numpy-core growth clause for 091, and read (or waive) 073's missing CI run, before main
moves.

## Addendum: the accept log's changed rows, attributed (2026-10-20)

The lane accepted on `2bb98c8`: `170b4e2` plus the reviews commit, 630/701 pass, 0 fail, history
line 83, not yet committed. Its changed rows against `e8ba20a`'s `accepted.json` are listed in
`build/wave-02/grown.txt`:
- 176 fuel rows;
- 3 bytes rows;
- 2 passes rows;
- 32 new checks, none gone.

**How I checked each row (EXECUTED).** `probes/predict.py` predicts every row from the entries'
own measured records, then compares the prediction with the lane's record
(`build/progress/latest.json`). The full table is `predict.txt`.
- **039 and 041's share:** 041's full judge record (`wasi_python-041/build/041/latest-full.json`,
  on `39cf425`, with 039 under it), minus main's accepted value at its base `9d89535`.
- **073's share:** its builder's full record on the rebuilt set
  (`wasi_python-073/build/073/latest-full3.json`), minus main's accepted value at `a6dfc17`.
- **The prediction** is the sum of the two shares. The residual is the wave's Δ minus the
  prediction.

### The three rows the lane asked about

1. **`pandas-io-formats`, +30,587,970,233 fuel and +995 passes: explained, no entry ejected.**
   - The "unexplained ~7 G and ~20 passes" are **039's**.
     - With jinja2 in the zip, 20 more tests pass: 997 against 977 (039's spec, line 864).
     - Its fuel rises +7.73 G (spec line 974; the 039 build review's record shows 66,376,362,782).
     - 039's growth text names this as "pandas-io-formats runs the Styler tests".
   - 041's "+22.8 G, +975" is measured **over 039's set**, not over main.
   - The chain: 58.647 G (977 passes) → 66.376 G (997, 039) → 89.221 G (1,972, 041's record)
     → 89.235 G (1,972, the wave).
   - The wave's counts and `passed_digest` `944be956ac40` are **identical** to 041's record.
   - The last +14.7 M is 073's unfreeze.
   - Against the summed shares, the residual is −77 M (−0.13 %).
2. **Snapshot bytes +739,926: explained as wizer's segment layout, not a defect.**
   - The prediction is +726,299 (039 and 041) − 1,691 (073) = +724,608, so the residual is
     +15,318 (0.034 %).
   - Per section, wave against 041's snapshot (`probes/segs.py`, EXECUTED):
     - code +502, identical to the plain binary's code delta (087's regex patch plus 073's C);
     - data +13,279;
     - custom 0.
   - Both snapshots have exactly **10,000 data segments**, so wizer is at its segment cap and
     merges neighbouring runs, zero gaps included.
   - The image's bytes therefore depend on where the heap's objects fall, not only on how many
     there are. The heap gained 087's and 073's static data (+1,920 on the plain binary) and
     073's larger bootstrap module, and holds tier A's larger frozen zip directory. That cause
     is INFERRED.
   - 073's own two builds, which differ by one import line (B1), already swung by 9.6 K: +7,950,
     then −1,691.
   - So "a few K either way" understated the noise. +15 K is the same effect. It is a size
     fact, with no behaviour behind it.
   - Plain `python.wasm`: +2,268, exactly 073's. The zip: +16,524,471, exactly 041's record.
3. **`test_no_cpython_test_module_is_built_in` +33,187,868: explained.**
   - It is a snapshot `run`: 039's +4,643,461, 073's +28,117,280, and a residual of +427,127.
   - The +202 % only reflects a small base (16.4 M).

### Every other row

- **Snapshot `run` rows (about 60 of them):** +32.9 M to +34.5 M. Rows that import pandas or
  matplotlib rise to +49 M to +51 M; the ctypes stand-in rises +84.9 M (prediction +83.6 M).
  - Every one carries a small positive residual, **+0.31 M to +0.54 M**. This is the interaction
    073 predicted ("the floor perhaps a few M more with tier A in the frozen zip directory"): the
    unfreeze now walks a heap that holds 2,014 more zip entries. It is smaller than predicted.
  - Large percentages on these rows only mean a small base.
- **Plain rows:** +45.7 M (the hard-exit row, 039's measured figure) to +54.7 M. The named
  exceptions match their predictions within ±3 M:
  - metadata +444.7 M (039);
  - GB18030 +907 M (039);
  - `test_resources_read_as_zipfile_reads_them` +4.31 G (039's member walks; prediction
    +4.31 G);
  - the fast reader's `padded`, `small` and `snapshot` cases (035's walks, 039);
  - `invalidate_caches` +99.7 M (039, as named);
  - `test_lxml_xml_job_matches_native` +64.6 M (prediction +56.3 M plus 073's +7.3 M);
  - the ctypes stand-in, plain +61.3 M (prediction +60.7 M).
- **The hard-exit row on the snapshot:** +13,961. As expected, it shows no 073 unfreeze.
- **Rows no record measured** (wave 01's new checks: 087's DENY_ALL and regex timeout rows, 083's
  and 089's three): plain +50.7 M to +51.0 M, snapshot +33.2 M to +34.4 M. That is exactly 039's
  start plus 073's unfreeze.
- **Upstream groups:**
  - pandas and numpy residuals run from −0.39 % (`pandas-reshape`, a fall) to +0.26 %
    (`pandas-tslibs`). That is within 073's reviewed band ("−0.14 % to +0.27 %, both
    directions", B4) plus 041's ±0.11 %, across two different bases.
  - `pandas-internals` +1.44 % and `pandas-libs` +1.13 % are predicted to within −0.03 % and
    +0.05 % (039's scans on small groups).
  - CPython's five groups are within 039's measured deltas, plus 073's unfreeze: `cpython-c`
    +55 M over 039's, and `cpython-a` and `cpython-b` below 039's.
- **numpy-core +393,135,543 (+0.252 %): explained, and it confirms M1.**
  - 039 and 041 give +113 M. The rest, about +280 M (0.18 %), is 073's unfreeze, which its
    review measured at +0.19 G.
  - 073's +4.48 G layout term is **absent** (residual −4.20 G), because 091 moved it into the fact.
  - The fact `string-comparisons` is **63,543,215,774**: +7.6 % on 091's quoted 59,054,444,847,
    inside the 10 % band, so no cause sentence is owed. It matches 073's own +7 % (61.44 G to
    65.73 G).
  - The landing notes should quote it, and replace 073's numpy-core clause with "+0.39 G, 039's
    scans and 073's unfreeze; the layout term is the fact string-comparisons, 63.54 G" (M1).
- **Passes:**
  - `pandas-frame` 10,853 (+1 on main's 10,852): counts and digest `6c737399d3bc` identical to
    041's record;
  - `pandas-io-formats` +995: see item 1.

### Addendum verdict

**Every changed row is explained by a claim, and no entry is ejected.**
- No row's residual against the entries' own records exceeds about 0.5 M absolute on a guest
  check, or 0.4 % on an upstream group.
- The two exceptions both have causes: numpy-core's −4.2 G (091) and the snapshot's +15 K bytes
  (wizer's segment cap).

What the landing notes must still carry:
- M1: 073's growth clause is corrected, and the fact quoted;
- the snapshot-bytes cause, one sentence;
- M2: 073's missing release run is read before main moves, or waived by the owner.

**Final verdict: lands as merged at `170b4e2`, accepted as `2bb98c8`, on M2.**
