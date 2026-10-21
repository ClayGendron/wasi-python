# Review of 045 — statsmodels, with formulaic, interface-meta and wrapt (the build review)

- **Date:** 2026-10-20 (the run's clock reads 2026-10-21 UTC)
- **Reviewer:** a fresh agent started by the lane. It wrote none of 045 and reviewed none of it.
- **Reviewed:** `spec/045-statsmodels` at `3aa663a` against its base `dbecd2d` (main plus the
  structural chain 103 to 109). The last code commit is `7be1837`. `7be1837..3aa663a` touches only
  `README.md` and the specification (EXECUTED: `git diff --stat`).
- **Run:** the builder's run **39533679276**, on `7be1837`. That is the exact code reviewed, so no
  second run was dispatched (AGENTS.md rule 8; the owner, 2026-10-20). It was read back with
  `gh run view --json jobs`, every `record-*` artifact, both `rebuild-ubuntu-*` artifacts and
  `rebuild-wheel-ubuntu-24.04`.
- **Re-ran:** these node ids, in the worktree, on the builder's set:
  `tests/unit/test_statsmodels_build.py`, `test_rules.py::test_carried_patches_follow_the_rules`,
  `::test_code_outside_src_names_no_context_document`,
  `test_v1_1_artifact_set.py::test_statsmodels_notice_carries_its_bundled_parts`,
  `::test_left_out_dataset_files_are_not_in_the_zip` and
  `test_v1_5_rebuild_from_pins.py::test_source_tree_matches_its_tarball[statsmodels]`. Result:
  10 passed, exit 0. `ruff check` and `ruff format --check` on `src` and `tests` are clean. Fuel
  probes ran through `wasi-python run --fuel` on three sets (below). No fast tier ran: CI's legs
  and the builder's `build/045/fast-1.txt` cover it, and no slot was needed.
- **Box:** 75 minutes, as the lane set it. The review closed inside it.

## Acceptance criteria against evidence

1. **Seen failing first:** met. READ: `build/045/seen-failing-base.txt` lists the eleven guest
   checks and the left-out zip check failing on the set before 045.
   `build/045/unit-seen-failing.txt` shows the unit checks failing before their code. The L5
   probe shows the notice check failing on a cut notice.
2. **The build:** met. EXECUTED from the run: every build job is green. Both rebuild hosts produce
   a `SHA256SUMS` that hashes to `14adfa5f7b5095d509a4bb9790622db56fc005a75ef2fbd4da67c7e0622bab5c`,
   the same as the builder's local set. `python.wasm` is `380883f2…`, the snapshot `25a28831…`
   and the zip `142d6043…`. The zero-patch step's `^28 passed` grep runs inside the build job,
   which is green. `MANIFEST` names the four pins, the recipes, step 59 and the patch (READ: lines
   65, 178, 224, 256-260, 267, 307).
3. **The same bytes everywhere:** met. EXECUTED: `the same bytes from every host` is green, and
   the two rebuild hosts' `SHA256SUMS` files are equal (`cmp`).
4. **The judge:** met for a builder, short of the lane's accept. On macOS, red lines are GREW
   only: own-guest 212, own-embedding 33, upstream-macos 1. Nothing is LOST and there is no G7.
   The two red Windows legs are not 045's (Note 3). `regen --check --online` was READ from
   `build/045/regen-check.txt`, not re-run.
5. **The numbers recorded:** **not met for one number.** The wheel's bytes are missing
   (Finding 1). Every other number is recorded.
6. **The release:** this is the wave's dry run, still to come. The gather job was skipped, so
   there is no `release-record-1`.

## Findings, most severe first

1. **Medium: the wheel's bytes are not recorded, and the wheel is now about 1 MB under the
   owner's 100 MB line** (`context/specifications/045-statsmodels.md`, *For the lane*, the line
   "the wheel's bytes are the run's `release-assets` (not read here)").
   Criterion 5 asks for the wheel's bytes. Decision 14 says "The wheel's growth is recorded
   against PyPI's limit (question 64)". The owner's answer to 64 is "wait on a decision until we
   cross the 100MB threshold", and the agent is to bring the question back "when a landing would
   cross 100 MB". EXECUTED: run 39533679276's `rebuild-wheel-ubuntu-24.04` holds
   `wasi_python-0.1.0a8-py3-none-any.whl` at **99,010,212 bytes**. The base run 39530569266 (on
   `dbecd2d`) has a wheel artifact of 91,470,969 bytes, against 98,834,007 here. So 045 adds about
   7.4 MB to the wheel.
   Failure: 045 itself stays under the line, by 0.99 MB (decimal), or by 5.85 MB against PyPI's
   100 MiB. But the wave lands as a whole. A wave tip with 045 and any other entry that grows the
   wheel by more than about 1 MB crosses the line before the owner hears about it. Wave 09's
   spec 100 (numpy on OpenBLAS) is the next build-class candidate.
   Fix text, for *For the lane*'s table, a new row: "| the wheel (`rebuild-wheel-ubuntu-24.04`,
   run 39533679276) | about 91.6 MB (run 39530569266's artifact, 91,470,969 bytes zipped) |
   99,010,212 | about +7.4 MB | question 64: under 100 MB by 0.99 MB; the next package crosses it |".
   The README's sizes row should carry the same figure.
   What closes it: the number written in, and question 64 brought back to the owner before the
   lane accepts a wave tip whose wheel would pass 100,000,000 bytes. The lane should measure the
   wheel at the wave's tip. This finding does not ask the owner to decide before 045 lands: 045
   alone does not cross the line.

2. **Low: the growth reasons leave out one cause, and Decision 14's last row is breached
   unnamed** (*For the lane*, "Rows that grow", and `--accept-growth`). Decision 14 expects every
   other golden job to grow by "the plain-start growth only", and calls any more a finding. Many
   do grow more. The `sqlite` job grows +23.4 M and imports only pandas. `callbacks` grows
   +20.7 M, `markup` +25.0 M, `excel` +27.3 M, `modelling` +63.5 M and `files_from_the_zip`
   +63.1 M, all against a start of +15.1 M. The stated reasons, zip members and metadata walks,
   do not cover the pandas-only rows.
   The probes (EXECUTED, `wasi-python run --no-snapshot --fuel`, the same runner each time):
   - 3,000 failed imports cost +24.7 M on 045's set against main's set. That is about 8.2 k fuel
     per import lookup.
   - `import pandas` costs +4.9 M over the start's growth.
   - A mixed set, 045's `python.wasm` with main's zip, gives +24.4 M for the same 3,000 misses,
     and only +0.64 M at `pass`.
   So the per-import cost comes from the binary, not the zip. It is INFERRED to be the 26 longer
   inittab entries that each builtin lookup scans. The same probe shows that 0.64 M of the start's
   "+15.1 M (25,668 per member)" is the binary's too.
   Failure: none in the build. But the accepted record would carry a reason that is not true for
   rows like `sqlite`, and Decision 14's last row would stand unanswered.
   Fix text: append to `--accept-growth`: "; and each import lookup about 8 k fuel more in the
   binary's longer inittab (26 entries; EXECUTED, 045's python.wasm with main's zip), so a job
   importing pandas pays +4.9 M over the start, and the golden jobs grow past Decision 14's
   plain-start row by that and by their version() reads and metadata walks". Add one sentence
   after the seaborn paragraph, saying Decision 14's last row is outside for the same causes.

3. **Low: the build shard is not on Linux** (*For the lane*, self-check item 5: "the notice and
   source-tree checks run in the build shard (Linux)"). EXECUTED: `record-build-build`'s
   platform is `darwin-arm64`. The job is "build and judge (arm64 macOS)". Fix text: "(the build
   shard, on arm64 macOS; Linux and Windows run the zip's left-out check and every guest check)".

## Notes

1. **"The bound was wrong" is a fair answer, and nothing should shrink in this specification.**
   The builder measured the growth three ways, and I read all three:
   - `build/045/size-2.txt`: only the 26 statsmodels archives and `inittab.o` changed. The
     state-space family is the top six inputs.
   - `build/045/olevel/sizes.txt`: `-O3` gives 6,063,407 bytes of code, `-O2` 5,886,567 and
     `-Os` 5,520,023. At most 0.54 MB comes from the optimisation level.
   - The ratio: 044's own accept line says scikit-learn added +9.00 MB to the binary against
     Pyodide's 6.0 MB (1.50). Decision 14's 0.92 came from numpy and pandas, so it does not fit
     Cython packages.

   The four-dtype expansion is upstream's design. Cutting dtypes would be a patch that changes
   behaviour, and §4.1 rules that out. The growth does not need the owner on its own: no
   constitution rule bounds `python.wasm`. It meets the owner only through question 64
   (Finding 1). If 64 binds, the levers are set-wide, not 045's: the `name` section is 14.1 MB of
   the binary, and `-Os` across the Cython packages would save about 9% of their code.

2. **Seaborn's +38.8 M is explained in kind.** These figures were READ from
   `build/045/fuel-probes.txt`:
   - one `entry_points()` walk costs +22.4 M over the start's growth;
   - the four `version()` reads cost +3.9 M;
   - seaborn's own `import statsmodels` costs 0.35 M.

   The builder's guess that the import overhead is "most of it, INFERRED, such walks inside those
   imports" is half right. The builder's own probe shows `import matplotlib.pyplot` at +3.5 M over
   the start, with no walk. Finding 2's per-import cost is the rest.

3. **Neither Windows red line is 045's.**
   - `test_a_forked_child_is_refused`: EXECUTED from run 39530569266's log, on `dbecd2d`. It
     fails the same way on the base. The chain fixes it at `727bd4c`.
   - `test_a_same_size_same_mtime_replacement_is_hashed_again`: a unit test of `src/`. 045
     changes no file under `src/` (EXECUTED: `git diff --stat dbecd2d..3aa663a -- src` is empty).
     The lane is fixing it on the chain. I could not read spec 100's run 39535794638 log back.

4. **Every grown row on the run is named.** EXECUTED: each shard record was compared with
   `context/progress/accepted.json`'s darwin-arm64 metrics. The run has 246 GREW lines
   (212 + 33 + 1). They are the three byte rows, the starts, the zip-directory checks (up to
   +10.1%), the metadata and import rows, and upstream `cpython-fs` (+257,958,402). One more row,
   `numpy-lib`, grew +7,993,591 (0.006%). That is under the ratchet's tolerance, and the log
   prints no GREW line for it.
   Linux and Windows have no accepted metrics, so they show no GREW lines. Finding 2 aside, each
   row falls in a class the claim list names.

5. **The judge is not weakened (rule 4).** Every change to an existing check adds names:
   - the package, licence, pin, source-tree and metadata lists;
   - `MESON_BUILDS`, `JOBS` and `PLATFORM_BOUND`;
   - the tree count, 27 to 28;
   - `own` gains `"statsmodels"`.

   No assertion was loosened. Nothing was added to `known_gaps.toml`, `tests/upstream/expected/`
   or `context/progress/`. `packages.toml` gains statsmodels as `later` (closer spec 095, the
   owner's answer) and the three wheels as `later` (spec 067).

6. **The claim list matches the diff.** It names the 14 new rows and the unit file, and the
   changed checks with their two unit fixtures (`test_build_progress.py`'s step list and
   `test_artifact_rules.py`'s synthetic set). No unclaimed row changed. The flags each begin
   "045:".

7. **Structure (4a):** nothing to score. No `src/` change. Step 59 is a 111-line shell step on
   step 58's pattern. The Kind line rightly does not carry **structural**.

## Constitution checks

- **§4.1:** one patch, `recipes/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.patch`. Its
  SHA-256 is `751e7190…dd58` (EXECUTED), as the specification says and `MANIFEST` records. The
  CHANGELOG names it. Its pull request is drafted at
  `context/upstream/patches/statsmodels-0.15.0/0001-datasets-from-a-zip.md`. `patch_errors` and
  the zero-patch tree check pass. Everything else is a recipe: the cross file, the stand-in's
  `get_version`, the four rename headers and the per-file include map. The cross file's
  `-Wno-return-type` is the same as pandas' and scikit-learn's.
- **§4.2:** five new pins in `downloads/SHA256SUMS`: the sdist, three wheels and MNE's licence at
  `2c4a3b03`. Each is fetched by one `get` line, with the digests the specification gives.
- **§4.4:** no new import. READ: step 60's link-map gate reports "4 names required, 3 forbidden, 0 findings" (`build/logs/60_link.log`), and every guest check is green on all three systems in the run.
- **§4.12:** `LICENSES/statsmodels.txt` (522 lines) holds the licence, `COPYRIGHTS.txt`, both
  folder licences, the six components the owner approved on 2026-10-20 with their line ranges,
  MNE's and numpydoc's pinned texts, and the datasets part. EXECUTED in the zip: 501 statsmodels
  members plus `METADATA`; 59 formulaic, 12 interface-meta and 15 wrapt; no `datasets/*/src/`
  member and no `rlsdata.txt`. Each of the thirteen left-out datasets keeps only `__init__.pyc`
  and `data.pyc`.
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. Finding 1 (Medium, the wheel's bytes) — written in. *For the lane*'s table gains the row in the
   review's fix text: the wheel 99,010,212 bytes (run 39533679276's `rebuild-wheel-ubuntu-24.04`),
   about +7.4 MB on run 39530569266's 91,470,969, under the 100 MB line by 0.99 MB. README's sizes
   row carries "the wheel 99.0 MB". *The wave* now says plainly that 045 lands after wave 09 (100,
   101, 097), whose numpy-on-OpenBLAS change may grow the wheel, so the lane re-measures the wheel
   on 045's rebase onto wave 09 before accepting and brings question 64 back to the owner first if
   it passes 100,000,000 bytes. The *Remaining* line no longer says the wheel was not read.
2. Finding 2 (Low, the per-import cost) — written in. The review's fix text is appended to
   `--accept-growth` word for word. A paragraph after the seaborn one says Decision 14's last row
   is outside for the same causes and one more: about 8.2 k fuel per import lookup from the
   binary's 26 longer inittab entries, with the review's probes and the six golden jobs' rows.
3. Finding 3 (Low, the build shard's host) — written in. Self-check item 5 now reads "the build
   shard, on arm64 macOS; Linux and Windows run the zip's left-out check and every guest check".

## Verdict

Lands once Finding 1 is written in: the wheel's 99,010,212 bytes recorded, and question 64
brought back to the owner before a wave tip's wheel passes 100 MB. The size growth past
Decision 14's bound is explained truly, and nothing in 045 should shrink.
