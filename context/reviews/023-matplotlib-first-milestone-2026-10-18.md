# Review of 023 — matplotlib, the first milestone (the build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of the specification or the build,
  and I am not the pre-build reviewer. I judged from the specification, its pre-build review
  (definitions A to E), the constitution (§4.1, §4.2, §4.4, §4.6 to §4.9, §4.12, §4.15, §5.6),
  specs 020, 035 and 051, the research memo, and the diff; the landing notes only told me what to
  re-run.
- **Reviewed:** `git diff 73fb50b...298a533` on `spec/023-matplotlib-first-milestone` (eight
  commits, 67 files, +3,291 −92), with the worktree's own artifact set
  (`python.wasm` `e0224891…`, snapshot `8eb9e357…`, zip `16ee747c…`).
- **Ran (EXECUTED, darwin-arm64, 10 cores, load average 25 to 100 from other sessions).** Nothing
  tracked was edited; no commit, branch, stash, checkout or `--accept`. Scripts and logs sit beside
  this file, in `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/023-buildreview/`:
  - `clone/`: `git clone --branch spec/023-…` (HEAD `298a533`) into the scratchpad, a third path.
    I copied in only the 45 pins main already had; the 16 new pins this host needs were fetched
    from their URLs by `00_download.sh` and verified (`clone/build/logs/00_download.log`).
    `scripts/build.sh --plain`: 13 steps, 8 min 44 s, exit 0 (`rebuild.log`).
  - `unpatched.log`: in the clone, matplotlib's patch moved aside, `scripts/build.sh --plain 55 60`.
  - In the clone, the patch put back and one line added to `build/kiwisolver-1.5.1/py/src/solver.cpp`,
    then `pytest … -k test_source_tree_matches_its_tarball` (mutants of spec 020's rule).
  - `wheel.log`: the wheel built in the clone as spec 028 builds it.
  - `runner_milestone.py` / `.txt`, `chmod_probe.py`: the milestone, the data grant, and tampering
    with the extracted data, through the real `wasi_python.run`, on both binaries.
  - `fuel.py` / `.txt`, `plotfuel.py` / `.txt`: start fuel through the judge's driver, each binary
    with each zip; the README's plot fuel.
  - `table_low.py`, `mutant_rules.py`: what sits at table indices 1 to 30 in both binaries; the
    callback scan with `PARSER_RULES` at 0, 20 and 30.
  - `ctor_mutant.py`: the constructor check on the real binary, and with one more constructor of
    an already-reviewed name.
  - `zipcheck.py` / `.txt`: the zip's new members, the backends, the inner archive.
  - `dl/`: the two Linux `pkgconf` wheels, fetched and hashed; `unicode.org/license.txt` diffed
    with the pinned Unicode terms. `up/`: shallow clones of kiwisolver and Pillow `main`, for
    `git apply --check`.
  - The judge in the worktree: `judge-fast.txt` (`-m "not slow"`), `judge-full.txt` (the full run).

## Acceptance criteria against evidence

1. **The checks exist and were seen failing first** — met. EXECUTED: with
   `0001-ft2font-enums-without-python.patch` moved aside, step 55 built and step 60 stopped:
   `ERROR: _GLOBAL__sub_I_ft2font_wrapper.cpp: a static constructor no review has read`, exit 1,
   no Wizer run (`unpatched.log`). The baseline failures of the milestone, data-grant and
   constructor checks are READ from the landing notes; I did not rebuild main's set.
2. **A full build from pins in a clean clone** — met. EXECUTED: the clone at `298a533` (a third
   checkout path, the new pins fetched over the network, not copied) applied all five patches
   (`applied 0001-…` lines in steps 40, 50 and 55) and gave **the same `SHA256SUMS` and `MANIFEST`,
   byte for byte, as the worktree's build**: `python.wasm` `e0224891…`, snapshot `8eb9e357…`, zip
   `16ee747c…`. `MANIFEST` has 62 `pin` lines, 22 `package` lines and a `recipe` line for every new
   recipe and each of the five patches (hashes equal `shasum` of the files). Both binaries run the
   milestone (below).
3. **The same-bytes rebuild on arm64 Linux** — not run here (no Linux host), as the landing notes
   say. Left to the release dry run. INFERRED risk is low: two macOS checkout paths and this third
   one agree, `test_artifacts_carry_no_build_path` passes, and the two Linux `pkgconf` wheels carry
   the binary at the same path, `pkgconf/.bin/pkgconf` (EXECUTED, `unzip -l`).
4. **`uv run pytest` green with `--accept-judge` and `--accept-growth`, growth inside Decision 6**
   — met, with Decision 6's two lower-than-expected numbers answered (below). The judge lines are
   under *The judge*.
5. **A release dry run** — not run here; the lane's.

### The milestone, run myself

- EXECUTED through the real runner (`runner_milestone.txt`), both binaries, the job's file granted,
  a writable `/out`, `/png` and `MPLCONFIGDIR`: stdout equals `tests/jobs/plot_line.expected`
  (RGBA `eab6d61b…3a73`, 300×400×4); the saved PNG, decoded by `harness/png.py`, has those pixels;
  the PNG is `b8759b7b…`, 22,439 bytes, on both; `/out` stays empty.
- EXECUTED (the full judge): `test_plot_line_job_matches_native` on both binaries,
  `test_goldens_reproduce_under_the_pinned_oracle` (the oracle reproduces `plot_line` here, its
  recording platform), `test_patched_callbacks_run` ×2, the dpi and kiwisolver checks.

### Pins (§4.2)

- EXECUTED: every one of the 16 new pins this host uses was fetched from its `get` URL in the clean
  clone and matched `downloads/SHA256SUMS`. The two Linux `pkgconf` wheels, fetched by hand, match
  their pins (`4ece8d4e…`, `bd3ee4b5…`).
- **The Unicode terms from `unicode-org/unicodetools@4fd8eca9` are an acceptable pin.** It is a URL
  plus a SHA-256, verified before use, at a full commit hash, so the bytes cannot move; it is the
  form the LLVM licence pins already use (`raw.githubusercontent.com/llvm/…/<commit>/…`).
  EXECUTED `diff` with today's `https://www.unicode.org/license.txt`: the same Unicode License V3
  text; only the copyright line (`2001-2024` against `1991-2026`) and a trailing SPDX line differ.
  That is the reason unicode.org cannot be pinned, as landing-notes item 4 says.

### The three carried patches (§4.1, spec 020)

- matplotlib 0001 is byte-identical to the pre-build review's re-made file (EXECUTED `cmp`). Its
  draft says `Status: merged …/pull/30291`; facts sheet 17 says when it goes.
- Pillow 0001 (two lines) and kiwisolver 0001 (21 lines) change only signatures: each adds the
  unnamed `PyObject *args` / `PyObject*` / `void*` parameter CPython passes (READ: every `-`/`+`
  pair). Each `fix.patch` under `context/upstream/18-…`, `19-…` equals the carried file (EXECUTED
  `cmp`). Both still apply to upstream `main` (Pillow `6085656`, kiwi `ef031dd`; EXECUTED
  `git apply --check`, exit 0), and Pillow's `main` still lists both with `METH_VARARGS` (READ).
- Each is hashed in `MANIFEST` and named in the CHANGELOG (READ). `apply_patches.sh` applies them
  (EXECUTED, the clone's logs). The exact-difference rule holds: in the clone, with matplotlib's
  tree left unpatched and the patch put back, `test_source_tree_matches_its_tarball[matplotlib]`
  fails naming the four files; one added line in kiwisolver's tree fails `[kiwisolver]`
  (`py/src/solver.cpp: modified`); on the worktree all 15 pass (`15 passed, 11 deselected`), the
  count the release workflow now greps.

### The callback scan's `PARSER_RULES` rule

- The reasoning holds **in these binaries**. EXECUTED (`table_low.txt`): table indices 1 to 30 are
  all `*_rule` or `_PyPegen_*` in both the baseline and the new `python.wasm`, in the same order.
  With `PARSER_RULES = 0` the scan reports exactly one finding, `single method ADD_STYLE_NAME:
  table index 1 … (_tmp_6_rule)`; with 20 or 30, none (`mutant_rules.txt`). So no real method sits
  at 1 to 20 today and nothing real is hidden.
- It rests on a fact about link order that nothing checks (Finding 3).

### The runner's data grant (§4.4, §4.15)

- EXECUTED (`runner_milestone.txt`), both binaries: `/usr/local/lib` lists `['python315.zip']`;
  the data grant refuses append, create, write, `mkdir`, `remove` and `rename` with
  `PermissionError` 63. `os.chmod` returns success in the guest, but it is WASI's no-op: the host
  mode stays `0o100644`, exactly as for the zip itself (`chmod_probe.txt`). With no root and no
  `MPLCONFIGDIR`, `import matplotlib` raises `OSError` as the README says.
- EXECUTED: between two calls I rewrote `matplotlibrc` and added `stylelib/evil.mplstyle` in the
  private folder. The next call read the archive's `matplotlibrc`, did not see the added file, and
  on the host both were restored and removed. The private folder is `0700` and holds exactly `lib/`
  and `mpl-data/`.
- READ: the data preopen goes through `_check_preopens` like every preopen; `_runtime_folders`
  judges the whole private folder (`_zip_known` returns its parent), so no grant can hold the data;
  user grants under `/usr/local/lib` stay refused. No new import: EXECUTED, the imports of the new
  and old `python.wasm` are the same 43; exports equal; no `qh_*` function is linked.

### Growth (Decision 6)

- EXECUTED (`fuel.txt`), exactly the landing notes' numbers: plain `-c pass` 150,988,365 →
  166,511,583; snapshot 81,868,626 → 83,372,077; plain `import numpy` 1,041,850,698 →
  1,057,526,128. The split: the old binary with the new zip gives 166,032,074, so the zip is
  +15.04 M of the +15.52 M, 23,840 fuel per new member, spec 035's slope. Plain start is under
  Decision 6's +47 M because spec 035's reader cut the per-member cost from 76,490 to about 25,000
  after Decision 6 was written; that answer is true and measured.
- `python.wasm` +16.1% against "about +19%": lower, explained by contourpy and `_qhull`'s wrapper
  in the memo's figure (READ; the breakdown below the memo's number is INFERRED by the builder).
  Lower growth is not a regression; I accept the answer.
- The zip +10,745,113 bytes against "about +11 MB": inside. The +95.9% is the right size for what
  was added (631 members, a 4.7 MB deflated data member; `zipcheck.txt`). The README's measured
  row gives the new sizes and fuel with their before values for fuel.
- Outliers spot-checked: the README's plot fuel, snapshot, no pre-import: fresh cache 7,558,480,329,
  kept 5,567,712,830 (`plotfuel.txt`; the notes say 7,559,402,576 and 5,566,539,879: a 0.02%
  difference from my different grant layout). Reasons given for `test_resources_read_as_zipfile_…`
  (+27%) and `test_packages_carry_their_metadata` (+43.5%) are plausible from the 36% more members
  and seven more METADATA files (READ the checks; not re-measured separately).
- **Q64:** the wheel built in the clone is 52,070,232 bytes (49.7 MiB); the notes say 52,070,134.
  The 98 bytes are the README inside METADATA (the notes' wheel predates the last commits;
  INFERRED). Largest members equal the notes' to the byte (EXECUTED).

### Licences (§4.12)

- READ (`build/artifacts/LICENSES/`): FreeType (LICENSE.TXT, FTL.TXT, BDF and PCF READMEs),
  HarfBuzz (COPYING, ms-use, the Unicode terms), SheenBidi, libraqm, matplotlib's whole `LICENSE/`
  folder plus Agg's `copying`, DejaVu's and STIX's licences and `pdfcorefonts/readme.txt`,
  kiwisolver, Pillow, pybind11, cppy, fontTools (with `LICENSE.external`), cycler, pyparsing,
  packaging (both licences). Every one is approved in §4.12's matplotlib list. FreeType's `dlg/`
  (BSL) is not compiled (EXECUTED, `compile_commands.json`), and its gzip module uses the shipped
  zlib. The one gap is FreeType's credit line (Finding 1).

## The judge

EXECUTED in the worktree on its own artifact set, without `--accept`.

The fast tier (`judge-fast.txt`): 1374 passed, 9 skipped, 46 deselected; `308/356 pass · 0 gap ·
2 blocked · 0 fail`; red only for growth (`grew 70`), `lost 0`.

The full run (`judge-full.txt`, 9 min 59 s, load average 53 falling to 18 over the run):

```
1406 passed, 9 skipped, 14 xfailed in 599.74s (0:09:59)
wasi_python v1: 340/356 pass · 14 gap · 2 blocked · 0 fail   (unit suite 1066/1073, 7 skipped)
blocked by: prior-art clones 1 · three systems 1
gaps close with: README 10 · questions-for-the-owner 2 · 2026-10-17-matplotlib-on-the-current-line 2
ratchet vs 4921daffeb: lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 23 · grew 85 · more 1 · judge changed: … and 25 more
RED: 85 metric(s) grew
```

- Red only for growth, which the lane accepts with `--accept-growth` and the landing notes'
  reasons (spot-checked above). `lost 0`. The two new gaps are the M2 ones, failing as
  `tests/known_gaps.toml` says. `test_callbacks_have_the_types_cpython_calls` is green, so spec
  051's binding holds.
- The load-sensitive door-deadline check (spec 030;
  `test_a_deadline_during_a_door_call_under_cancel_is_named`) **passed** in this run, at load 18
  to 53. It failed once in the builder's run at load 37; spec 052 is fixing it.
- `ruff check src tests` and `ruff format --check src tests`: clean (EXECUTED). The hits `ruff`
  reports under `scripts/` are older than this branch and outside the rule.

## Findings, most severe first

1. **Medium. FreeType's licence requires a credit line in the distribution's documentation, and
   none ships.** (`README.md`; `LICENSES/freetype.txt` lines 99 to 103 and 166 to 170; §4.12)
   - The defect. The FTL says "Redistribution in binary form must provide a disclaimer that states
     that the software is based in part of the work of the FreeType Team, in the distribution
     documentation", and gives the text: "Portions of this software are copyright © <year> The
     FreeType Project (https://freetype.org). All rights reserved." Shipping the licence file is
     not that disclaimer. No README, CHANGELOG or wheel text says it (READ, `grep`).
   - Failure. 0.1.0a6 (or whichever release first carries 023) puts FreeType in `python.wasm` on
     PyPI and GitHub without the credit the licence makes a condition of binary redistribution.
   - Fix. One line in the README (it is the wheel's long description), for example in *matplotlib
     in the guest* or beside the licences: "Portions of this software are copyright © 2026 The
     FreeType Project (https://freetype.org). All rights reserved." (the year of the FreeType
     version used, as the FTL asks: 2.14.3's headers say 1996-2026, READ). Optionally a rules check that the README carries it while
     FreeType is pinned.

2. **Medium. The constructor check compares names as a set, so a second constructor with a name
   already reviewed passes.** (`tests/harness/constructors.py:62-69`)
   - The defect. `constructor_errors` flags a found name not in `REVIEWED_CONSTRUCTORS`, but two of
     the reviewed names are generic: `__cxx_global_var_init` (clang names the first guarded
     static's initializer so in every C++ file) and `_GLOBAL__I_000100` (any file with
     `init_priority(100)`). EXECUTED (`ctor_mutant.txt`): with one more `__cxx_global_var_init`, or
     one more `_GLOBAL__I_000100`, appended to the real list, the check returns no error.
   - Failure. A later pin of matplotlib, pybind11 or Agg adds a namespace-scope static in another
     file whose initializer touches Python (the 3.11.2 enum class), named
     `__cxx_global_var_init`. Step 60 passes, and step 80's Wizer hangs, the class the check exists
     to stop.
   - Fix. Compare the whole list: `found == list(REVIEWED_CONSTRUCTORS)` (order is link order and
     is stable, as the reviewed list already records), or at least a count per name
     (`Counter`). One unit check with a duplicated name.

3. **Low. The scan's `PARSER_RULES` exemption rests on a link-order fact nothing checks.**
   (`tests/harness/callbacks.py:59-60, 271-272`)
   - The defect. Any single definition whose function sits at table index 1 to 20 is skipped. That
     is right only while wasm-ld gives those indices to the parser's rules. Today it does, in both
     binaries (EXECUTED), so nothing is hidden now.
   - Failure. A later link (a new library linked first, a CPython change) moves a real `PyMethodDef`
     callback to index 12; its type mismatch is skipped in silence, and the guest traps at the call.
   - Fix. Skip only when the name section names the function at that index `*_rule` or
     `_PyPegen_*`, or have the scan fail when indices 1 to `PARSER_RULES` carry any other name. The
     member rule's older assumption could take the same guard.

4. **Low. Rebasing onto main has obligations the lane should check against this review.**
   (READ, `git diff 73fb50b main`)
   - `CHANGELOG.md`: main's `0.1.0a5 — unreleased` is about to be released without 023, so 023's
     entry must move to the next unreleased section; as written it would land in a5's notes.
   - `src/wasi_python/runner.py`: spec 054 changed `_run_checked` and the preopen list (+478
     lines); the merged grant order (zip, then data, then the import-path entries) is new code
     the review has not seen. Its checks (`test_matplotlib_data_is_granted_read_only`,
     `test_usr_local_lib_holds_only_the_zip`, 054's import-path checks) must pass on the merge.
   - Spec 049's API freeze: `MPL_DATA_MEMBER` and `MPL_DATA_GUEST` become internal names
     (`api.internal_names`); the README must not name them in code spans (it does not today), and
     `tests/harness/api.py --check` must pass.
   - README conflicts in the facts table; `context/upstream/README.md`'s numbering (17 to 19) does
     not collide with main.

5. **Low. Two documents are stale or misplaced.**
   - `README.md` still says "build from pinned sources, downloads present | 5 min 41 s"; with steps
     37 and 55 the build took 8 min 13 s (the notes) and 8 min 44 s here, under load. Re-measure or
     date the row. `pyproject.toml`'s `description` still says "with numpy and pandas compiled in".
   - Decision 5 says the extraction's time "goes in the memo as a benchmark fact"; it is only in
     the landing notes (89.6 ms, 2.4 ms per call). §4.9 puts wall-clock in a research memo: add it
     to the matplotlib memo.

6. **Low. A failed constructor check leaves the unchecked `python.wasm` in `build/out/`.**
   (`scripts/steps/60_link.sh:152-154`)
   - EXECUTED: after the unpatched step 60 failed, `build/out/python.wasm` (37,029,521 bytes) was
     still there. `scripts/build.sh --resume` reruns step 60, so it is safe; a named
     `scripts/build.sh 80 90` would snapshot that binary and hang.
   - Fix. Remove `$OUT/python.wasm` before `die`, or link to a temporary name and move it after
     the check.

7. **Low (optional). No judge check runs matplotlib through `wasi_python.run`.** The milestone
   runs through the judge's driver, which extracts the data with `extractall`; the runner's own
   extraction is covered by unit checks on synthetic zips and by the listing and permission checks.
   I ran the milestone through the runner (above): it matches. A cheap guard: one runner check that
   `import matplotlib; matplotlib.get_data_path()` lists the 40 fonts' folder and reads
   `matplotlibrc`.

### The builder's questions for the review

- `PARSER_RULES` for singles: sound for these binaries (EXECUTED), fragile across links (F3).
- The runner: refusing `\` and `:` is right for Windows; judging a member's type by its mode's
  type bits, with 0 meaning a plain file, is right (the inner archive's members are written with
  `0o100644`, EXECUTED); keeping a Windows file whose CRC-32 and size are right matches `_copy_zip`.
- `tests/harness/constructors.py` as a build input outside `MANIFEST`: acceptable. It decides only
  whether the build stops, never the bytes, so the same-bytes rule is not touched.
- Decision 6's two lower growths: answered and measured (above).

## Constitution checks

- **§4.1:** five patches, each recorded, hashed, named, drafted or (matplotlib) merged upstream;
  the 15 trees equal tarball plus patches; mutants fail (EXECUTED). Holds.
- **§4.2:** every new input pinned and fetched-and-verified here; the stand-in replaces
  setuptools_scm; meson runs the pinned build-Python (READ, the cross file); pkgconf is the pinned
  binary with its search path replaced; CMake is pointed at nothing. Holds.
- **§4.3, §4.4:** one target; no new import; `target_features` fixed at the line's ten. Holds.
- **§4.6:** the set keeps its shape; the data is a member of the zip, not a new artifact. Holds.
- **§4.7:** the stand-in and harness code are original (READ). Holds.
- **§4.8:** pkgconf, pybind11 and cppy are build inputs only; nothing unpacks outside `build/`.
- **§4.9, §4.10:** checks count; the extraction time belongs in a memo (F5).
- **§4.12:** every licence approved and shipped; FreeType's credit line missing (F1).
- **§4.15:** the data grant is read-only, inside the 0700 private folder, judged with the zip;
  no default loosened (the extraction is the runtime's own file, owner's question 2). Holds.
- **§5.6:** reviewed by a fresh agent with the spec and the diff. **§7:** nothing tripped.

## Verdict

**Lands once F1 and F2 are fixed.** F3 to F7 are fixed or answered in writing (F4 is the lane's
checklist for the rebase). Every acceptance criterion this host can run is met with evidence I
produced myself. That evidence: a third-path clean clone, with its new pins fetched over the
network, gave the same `SHA256SUMS` and `MANIFEST`. The milestone is pixel-equal on both binaries
through the real runner. The build without the patch stops at step 60 as stated. The 15 trees and
the patch rule hold under mutants. The full judge has 0 failures and loses nothing. Criteria 3
and 5 (the arm64 Linux rebuild and the release dry run) remain the lane's.

One line: the build does what spec 023 says and rebuilds to the same bytes. Before it lands, add
FreeType's required credit line and make the constructor check compare the whole list, so a
reused name cannot slip through.

## Disposition (filled in by the author, then confirmed by the reviewer)

The builder's disposition is in `build/reviews-evidence/023-buildreview/disposition.md` and in the
specification (`7ccf316`). In short:

1. F1 — fixed in `93f1f54`: the README carries FreeType's credit line; a rules check
   (`test_the_readme_carries_the_licences_credit_lines`, `scan.credit_errors`) holds it while a
   `freetype-*` file is pinned.
2. F2 — fixed in `8500f38`: `constructors.list_errors` counts each name, then compares the order;
   the reviewed list is now in link order; unit checks in `tests/unit/test_constructors.py`.
3. F3 — fixed in `8500f38`: a single at index 1 to 20 is skipped only when the name section names
   the function there `*_rule` or `_PyPegen_*`. The member rule's older assumption is left as it
   was, with a reason given.
4. F4 — answered: the rebase waits for the 0.1.0a5 tag; the builder wrote out the lane's checklist.
5. F5 — fixed in `93f1f54`: the README's build time, its first line, `pyproject.toml`'s description
   and the package docstring are updated; new memo
   `context/research/2026-10-18-matplotlib-data-extraction-time.md`.
6. F6 — fixed in `cbac924` and `8500f38`: `scripts/steps/constructors.sh`'s `check_constructors`
   removes a failing binary; a unit check covers it.
7. F7 — fixed in `af59f3c`: `test_matplotlib_finds_its_data_through_the_runner`.

## Confirmation (2026-10-18)

- **Reviewer:** the same fresh agent; not the author.
- **Reviewed:** `git diff 298a533..7ccf316` (15 files, +369 −42) and the disposition.
- **Ran (EXECUTED).** Outputs are beside this file in the scratchpad (`mutants2.py` / `.txt`,
  `f6.log`, `rebuild2.log`, `judge-fast2.txt`, `touched.txt`):
  - My F2 and F3 mutants, run again against the new code on the real `python.wasm`
    (`mutants2.txt`).
  - Step 60 in my scratch clone, fast-forwarded to `7ccf316`, on step 55 archives built without
    matplotlib's patch (`f6.log`).
  - A full `scripts/build.sh --plain` of `7ccf316` in that clone (`rebuild2.log`).
  - The fast tier, the touched checks, and `tests/checks/test_v1_3_matplotlib.py` whole, all with
    the worktree's own artifacts.
  - I did not run the full judge again. The builder's fresh run (342/358, 0 fail, lost 0) agrees
    with my fast tier, and the code changes are all in the judge's checks and step 60's gate. The
    artifacts are byte for byte the ones I judged in full.

### Each disposition against its finding

1. **F1: closed.** READ: the README's quote matches `docs/FTL.TXT`'s required text word for word
   ("Portions of this software are copyright © <year> The FreeType Project
   (https://freetype.org). All rights reserved."), with 2026 as the year, the year 2.14.3's
   headers name. It sits in the README, which is the wheel's long description, so it ships with
   both the GitHub release and the wheel. The rules check passes (EXECUTED, fast tier). One note,
   not a finding: `FREETYPE_CREDIT` fixes the year at 2026, so moving the FreeType pin to a
   release with a later year means editing this constant and the README together. The check then
   fails until both say the same year, which is the behaviour we want.
2. **F2: closed.** EXECUTED (`mutants2.txt`): the real list gives no error. One more
   `__cxx_global_var_init` gives `… a static constructor no review has read (1 more than
   reviewed)`, and one more `_GLOBAL__I_000100` the same. The list reversed gives "another order
   than reviewed". One name removed gives "reviewed, but no longer linked". Unit checks: 39 passed
   across `test_constructors.py`, `test_callbacks.py` and `test_build_scripts.py`.
3. **F3: closed.** EXECUTED (`mutants2.txt`): the real scan gives no finding, with 1,989 singles,
   as before. With the function at index 1 renamed `Real_method`, with its name removed, or with
   the whole name section cleared, the scan reports the `ADD_STYLE_NAME` record as a finding. So
   the exemption now needs the name, and without names nothing is skipped. READ:
   `_parser_rule` cannot raise a `KeyError`, because `_method_entry` already requires the index
   to be in `elements`. I accept leaving the member rule as it is: it predates this spec, and its
   cost is stated in spec 051's docstring.
4. **F4: answered, accepted.** The checklist covers what my finding listed:
   - the CHANGELOG entry moves to the next unreleased section;
   - `runner.py` is merged with spec 054, keeping the order zip, then data, then the import-path
     entries, and the named checks are run on the merge;
   - spec 049's `api.py --check` passes with the new names internal;
   - the README is merged by hand;
   - the full judge runs again.

   **I add one item:** the lane compares the rebased `runner.py` hunk by hunk with this reviewed
   diff, because that merge is new code no reviewer has seen. Main changed no build-class file
   since `73fb50b`, only `tests/harness/paths.py` (READ, `git diff --stat`). So the rebase should
   not change the artifacts, and `MANIFEST` changes only if a hashed recipe does.
5. **F5: closed.** READ: the README's build row (8 min 13 s, with its source), its first line,
   `pyproject.toml`'s description and the package docstring. The memo is dated and labelled, and
   it records wall-clock time as benchmark facts only.
6. **F6: closed.** EXECUTED (`f6.log`): step 60 linked the unpatched archives and printed
   `_GLOBAL__sub_I_ft2font_wrapper.cpp: a static constructor no review has read` and `… it is
   removed`, exit 1. Before the run, `build/out/` held a stale `python.wasm` (37,029,521 bytes,
   left by my first experiment). After the run it held none.
7. **F7: closed.** EXECUTED: `test_matplotlib_finds_its_data_through_the_runner` passes on the
   worktree's set. It goes through the real `wasi_python.run` and checks three things: the data
   path, the 40 fonts in `fonts/ttf`, and `matplotlibrc` with backend `Agg`.

### The rebuild and the judge

- EXECUTED (`rebuild2.log`): `7ccf316` rebuilt from pins in my clone (exit 0). `SHA256SUMS` and
  `MANIFEST` are identical to the worktree's: `python.wasm` `e0224891…`, snapshot `8eb9e357…`,
  zip `16ee747c…` (unchanged from the reviewed build), and `MANIFEST` `01fbade7…` (new, as the
  builder says).
- The fast tier (`judge-fast2.txt`): `1385 passed, 9 skipped, 46 deselected`; `310/358 pass ·
  0 gap · 2 blocked · 0 fail · 46 deselected (unit suite 1075/1082, 7 skipped)`; `ratchet vs
  4921daffeb: lost 0 · … · gained 20 · grew 70`. It is red only for growth, the same growth list
  as before.
- `tests/checks/test_v1_3_matplotlib.py` whole: 8 passed and 2 xfailed. The two xfails are the
  M2 gaps. The touched checks (the callback scan, the constructors and features, the credit line,
  the 15 source trees): 30 passed, 2 xfailed.

### Verdict

**Confirmed, it lands after its rebase.** Every finding is closed or answered. The lane rebases
after the 0.1.0a5 tag, using the builder's F4 checklist plus the item above. It runs the full
judge on the rebased commit, and it runs criteria 3 and 5, the arm64 Linux rebuild and the
release dry run.

One line: all seven findings are fixed or answered. Each fix holds against its mutant, and the
artifacts are byte for byte the reviewed ones. Spec 023 lands once it is rebased onto main after
the a5 tag.
