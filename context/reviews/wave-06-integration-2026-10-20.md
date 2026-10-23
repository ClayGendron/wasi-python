# Review of wave 06: integration of 043, 037 and 096

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent. I wrote and reviewed none of the three entries.
- **Reviewed:** `wave/06` at `d7fb1e6`. The chain is main `c091f3d`, then 043 (`fb33e20`), then 037 (`40f30cd`), then 096 (`d7fb1e6`).
- **Time box:** 45 minutes. All three entries are build-class, which is within the six allowed.
- **Run:** none of my own. The lane rebuilds the set in the main tree at `d7fb1e6`. `git diff 88e3f65 d7fb1e6 -- recipes scripts downloads .github src` lists exactly two files, 096's two patches (EXECUTED). `88e3f65` is the commit 037's set `40281c40` was built from. So the lane's set is 037's set plus 096's two patches, and nothing else.
- **Re-ran:** nine `test_rules.py` node ids and `tests/unit/test_callbacks.py`, before any `build/lane.lock` existed. I ran them in a `git archive d7fb1e6` export in my scratchpad, with no artifact set. Result: 40 passed, 1.89 s (`nodes.log`). The rules ids:
  - `test_carried_patches_follow_the_rules`
  - `test_specifications_have_their_header_and_sections`
  - `test_specifications_have_no_open_question`
  - `test_landed_specifications_cite_an_existing_review`
  - `test_known_gaps_are_well_formed`
  - `test_release_shards_cover_the_judge`
  - `test_every_package_names_its_own_suite`
  - `test_release_judges_in_shards`
  - `test_the_readme_carries_the_licences_credit_lines`

  No pytest ran in the main tree, and none ran while a lock existed.
- **Probes** (read-only, files beside this review):
  - `probes/pastimage.py` names each record behind check 3's "past the image" counters on 037's `python.wasm` (`pastimage-037.txt`).
  - `probes/predict.py` predicts every metric row from 037's measured records (`pred-037-vs-main.txt`).

Each item is labelled EXECUTED, READ or INFERRED.

## Acceptance criteria against evidence

### 1. Range-diffs (EXECUTED; `rd-037.txt`, `rd-096.txt`)

**043** was reviewed on `fb33e20` by its delta review, so I only confirmed one thing about it: `git diff 54022dd fb33e20` (043's last move) equals `git diff 41bcc0f c091f3d` (main's move) but for one roadmap line in `context/`. That line is the contourpy mention in 066's line.

**037**, `54022dd..4c39f89` against `fb33e20..40f30cd`:
- All 25 commits show `=`. The rebase was clean, as the message says.
- `40f30cd` is new. It adds only `context/reviews/037-scipy-delta-2026-10-20.md`.
- A second check: `git diff 4c39f89 40f30cd`, less the delta review, is byte-identical to `git diff 54022dd fb33e20`. So the rebase brought in 043's context-only move and nothing else.

**096**, `c091f3d..4d78a1a` against `40f30cd..d7fb1e6`:
- Ten commits show `=`. One shows `!`: the build commit `15f1d18` → `00e53b6`.
- That commit differs only by the three named hunks:
  - the README's patch row, 17 → **19**;
  - the README's *How it is built* list, seventeen → **nineteen**, with 096's two inserted;
  - the CHANGELOG: 096's bullet first, then 037's whole.
- `d7fb1e6` is new. It changes only the CHANGELOG's function count (5,360 → 5,893, "on the set with scipy") and the spec's rebase note.
- **Build-path identity:** I hashed the `+` and `-` lines of 096's diff before and after the rebase for `recipes/`, `scripts/`, `src/`, `.github/`, `downloads/`, `tests/`, `MANIFEST` and `LICENSES`. Every one is byte-identical (`recipes` `f12a8157`, `tests` `9fcca837`, the rest empty). So nothing of 037's under `tests/` was removed by the auto-merges either: a removal would have shown as a `-` line.

**Nothing changed that a builder did not name.**

### 2. Cross-entry interactions

#### (a) 096's slot scan on the merged set (EXECUTED and READ)

I re-ran `scan_slots` (the tip's `tests/harness/callbacks.py`) on 037's `python.wasm` (84,794,265 bytes, set `40281c40`).
- **Summary:** 554 types, 461 specs, 246 modules, 5,893 functions, 18 metatypes, 1 type named at run time, 0 unreferenced type candidates, 67 specs with slots past the image, 15 module slot arrays past the image.
- **Findings:** exactly kiwisolver's four `tp_clear`.
- This matches the builder's note in every number. Every minimum and bound of check 3 holds.

**The 15 module slot arrays past the image.** I listed them by name.
- Main's seven are Pillow's `_imagingmorph` (its array is empty) and matplotlib's `_c_internal_utils`, `_image`, `_path`, `_tri`, `_backend_agg` and `ft2font`.
- 043 adds two: matplotlib's `_qhull` and `_contourpy`.
- 037 adds six: `pyduccfft`, `_fmm_core`, highspy's `_core`, `_highs_options`, `_pava_pybind` and `_distance_pybind`.
- Every one of the 15 has `m_traverse`, `m_clear` and `m_free` all 0. The scan does read those three fields; only the `m_slots` array goes unread.

**Is skipping them safe?** Yes, for three reasons.
1. **The types are fixed by pybind11's own code (READ).** In pybind11 3.1.0 (the copy in `plot-tools`; `scipy-tools` holds the 3.1.0 dist-info), `init_slots` fills the array at run time, which is why it lies in `.bss`. It writes two function slots:
   - `Py_mod_create` = `cached_create_module(PyObject *, PyModuleDef *)`, which is `(i32, i32) -> i32`;
   - `Py_mod_exec` = `exec_fn`, whose parameter type is `int (*)(PyObject *)`.

   The C++ compiler enforces both signatures, and no package's own code is involved.
2. **Every one is imported by the judge.** The dotted-builtins checks import every dotted builtin, with scipy's 95 as their own run (`test_scipys_dotted_builtins_keep_their_import_names`). An import runs `Py_mod_create` and `Py_mod_exec`, so a type mismatch would trap there.
3. **The 67 specs past the image are all false shapes.** 43 more than main's 24, and none is a real `PyType_Spec`:
   - about 55 are Cython records whose "slots" word is `0x70000000`, the static refcount, with "names" such as `qr_update` or `__setstate_cython__`;
   - the rest are text or keyword lists (`origin`, `lag`, `_csv.Error` …).

**Is it counted?** In the scan, yes. In the record, no. The coverage line is 318 characters and `plugin.py` keeps 240 of them (`line.strip()[:240]`). What `latest.json` loses is exactly "0 suites past the image, 15 module slots past the image, 0 NULL function slots". This is 096's build review's L2, already a follow-up. Neither counter has a bound in `SLOT_MAXIMUMS`. See L2 below.

#### (b) Patch counts (EXECUTED and READ)

- `recipes/patches/` holds **19** `.patch` files:
  - OpenBLAS 3; numpy 2, kiwisolver 2, matplotlib 2, regex 2, scipy 2;
  - libxml2, lxml, networkx, pandas, pillow and qhull 1 each.
- The README's row says 19. Its "merged upstream" list names matplotlib's enum fix, qhull's format strings, two of OpenBLAS's, kiwisolver's `tp_clear` and lxml's `fake_cython`.
- The *How it is built* list says "nineteen" and names 19 patches. I counted them one by one.
- **The README's prose at line 56 still says "seventeen carried patches"** (L1). It said "ten" on 096's own tip, where the row said 12, so this staleness is inherited.
- `context/upstream/` numbers its drafts 26 and 27 (037) and 28 and 29 (096). There is no new clash; 21 twice is old.
- `test_carried_patches_follow_the_rules` passes.

#### (c) Tree count and known gaps (EXECUTED)

- **Tree count:** `release.yml` says "All twenty-five trees" and greps `^25 passed`. `pins.SOURCE_PATTERNS` has 25 keys: main's 22, plus contourpy (043), plus openblas and scipy (037). qhull was already counted. 096 patches two existing trees and adds none. Along the chain the count goes 22 → 23 → 25 → 25.
- **Known gaps:**
  - `git diff c091f3d fb33e20` removes exactly 043's two M1 gaps (`test_delaunay_triangulation_runs` and `test_contour_runs`) and their comment.
  - `git diff fb33e20 40f30cd` adds exactly 037's seven: `cpython-c-pydoc-imports-scipy`, and the matrix market, Sobol and ctypes-values gaps on both binaries. Six of them name spec 038 as their closer.
  - 096 leaves the file untouched (0 lines).
  - `test_known_gaps_are_well_formed` passes.

#### (d) kiwisolver's patch 0002 against matplotlib and 043 (READ)

- **What the patch does:** it changes four `*_clear` functions from `void` to `int` and adds `return 0`. That is all.
- **Callers:** if kiwisolver calls these from its deallocs, it ignores the result, so the call still compiles and behaves the same. The build compiled it.
- **0001 and 0002 together:** 0002 applies after 0001 on the fresh tarball (096's pre-build review, and the build).
- **matplotlib reaches kiwisolver only through constrained layout** (`_layoutgrid`). None of 043's checks uses it: not `plot_contour`, not contourpy's one-thread check, not the triangulation checks (grep, EXECUTED).
- **The checks that do touch kiwisolver** are 023's `test_kiwisolver_raises_unsatisfiable_constraint`, the `plot_callbacks` job (patch 0001's) and 096's new cycle check.
- **Fuel:** before 0002, a collection that met a kiwisolver cycle trapped. Every existing check passes, so none of them met one. The patch therefore moves no existing row beyond the four functions' extra instruction on paths no check runs (INFERRED).
- **lxml's line:** it changes `lxml/html/diff.py` only. pydoc's apropos, which imports every builtin in `cpython-c`, takes a zip module's synopsis from `get_source`. That returns `None` in a bytecode-only zip, so apropos does not import `diff` (INFERRED from pydoc's `ModuleScanner`). Only 096's new check imports it.

### 3. The reviews on the tip (READ)

- **On the tip:** 037's spec, design, build and delta reviews; 043's spec and build reviews; 096's spec and build reviews.
- **043's delta review is not on the tip.** It exists only as `scratchpad/043-buildreview/043-matplotlib-second-milestone-delta-2026-10-20.md`, and it is in no commit (`git log --all` finds nothing). See N1.

## Findings, most severe first

### M1 (Medium, lane): 037's restated `--accept-growth` lost the clause for the two pandas groups whose passes move, and 043's stop condition will trip on 037's share

- **What (READ).**
  - 037's build notes measured the scipy-dependent pandas tests that now run, because `importorskip("scipy")` no longer skips them:
    - `pandas-frame`: +73 passes, +10.6 G;
    - `pandas-groupby`: +1 pass (`sem`, importing `scipy.stats`), +8.07 G.

    Its first `--accept-growth` text (spec line 1243) says "pandas-groupby's one new pass and pandas-frame's 73 import scipy".
  - The paste-safe restatement the lane will use (line 1536) dropped that clause. The claim list never says a pass moves.
  - Those numbers were measured at `2687418`: wasi-sdk 33, no 043, before 091's numpy-core split. No record on `40281c40` has them. The delta review measured only CPython's groups, and the branch run's Linux shards compare no passes or fuel against darwin.
- **043's stop condition.** 043's delta-review text says the landing stops "if the lane's judge shows any of those groups [numpy-core, pandas, cpython-a to c] growing by more than 1%, or any pass moving". On this wave it will trip on 037's share:
  - `cpython-c` +6.29%;
  - `pandas-frame` and `pandas-groupby` passes;
  - probably `numpy-core`, which grew +1.18% at `2687418`.
- **Fix (the lane, in the accept text, no rebuild):**
  - Restore the clause in 037's `--accept-growth`: "pandas-frame's 73 and pandas-groupby's one new passes are tests that skipped without scipy; they import it (+10.6 G and +8.07 G at 2687418)".
  - Judge 043's 1%-and-passes condition on the **residual after 037's share**, using the table in criterion 4. A pass that moves anywhere other than those two groups stops the landing.

### L1 (Low, README): the prose still says "seventeen carried patches"

- README line 56 says "seventeen". The row and the list say 19.
- **Fix:** write "nineteen carried patches", and add *kiwisolver* (or *matplotlib in the guest*, where kiwisolver is described) to the places it names. Do it in a README-only commit. It need not hold the landing (rule 6b).

### L2 (Low, judge follow-up for 096's L2): the "past the image" counters are unbounded and the record drops one of them

- **The counters are unbounded.** `SLOT_MAXIMUMS` bounds only "unreferenced type candidates" and "types named at run time". A future package whose hand-written `PyModuleDef` slots or `PyType_Spec` slots land in `.bss` would pass check 3 unread. Today all 15 such arrays are pybind11's (or empty), so nothing is missed now.
- **The record drops one of them.** `latest.json` loses "15 module slots past the image" to the 240-character cut.
- **Suggested (not for this landing):** when 096's L2 follow-up shortens the summary, also name the module slot arrays allowed past the image, the way `SLOT_NAMED` names records. That is pybind11 3.x's modules plus `_imagingmorph`. Then a 16th array becomes a finding.

### N1 (note, lane): copy 043's delta review before the landing commit

Copy it from `scratchpad/043-buildreview/043-matplotlib-second-milestone-delta-2026-10-20.md` into `context/reviews/` in the lane's reviews commit, and cite this review. Without it, `test_landed_specifications_cite_an_existing_review` has only 043's build review to find.

### N2 (note, lane): the expected set

- 037's note says the lane's rebuild "should give `40281c40`". That no longer holds in the wave.
- The lane's `SHA256SUMS` should differ from `40281c40` in exactly four lines: `MANIFEST`, `python.wasm`, `python-snapshot.wasm` and `python-stdlib.zip`.
- Its 64 `LICENSES/` lines should be identical.
- `MANIFEST` should gain exactly two `recipe` lines, for kiwisolver 0002 and lxml 0001. Any other difference is a finding.

### N3 (note, lane): the flags, joined in wave order

Each flag keeps only its last value (wave 01's L1), so pass one string per flag:
- `--accept`: "Wave 06: 043, 037, 096 …", naming the lane's own `SHA256SUMS`;
- `--accept-judge`: 043's, 037's and 096's texts, in that order;
- `--accept-growth`: 043's, 037's with M1's clause restored, and 096's. 096's byte numbers are on 086's base; restate them as "+8, +1, +29 over 037's set".

There is no `--retire`, no `--accept-fewer-passes` and no `--partial`.

### N4 (note): no dry run of the merged tip

- Each entry has its own release run, as rule 2 asks:
  - 043: 39369636353;
  - 037: 39382879444;
  - 096: 39386471189, on `c091f3d`, Windows included.
- No run has judged the three together.
- The slot scan reads the module the same way on every host, and 096's new checks run under wasmtime, so a Windows-only difference from the merge is unlikely (INFERRED).
- No tag may follow anyway: the F4 ruling says no tag carries 037 without 038, and rule 6b's dry run comes before any tag.

## 4. The growth claims: the rule the lane uses

**Base.** Let Δ be a row's metric on the lane's record minus its value in main's `accepted.json`. Main is `c091f3d`, and its rows are `f70c666`'s: `python.wasm` 41,169,347, snapshot 45,444,036, zip 38,723,140.

**This base is the one each entry measured against:**
- 043 measured against 086's accepted set, whose bytes are equal;
- 096 measured on main's set;
- 037 measured against 043's set, and its delta review against `f70c666`.

**How the shares combine.** 037's records on `40281c40` already contain 043. So the **prediction** is 037's measured value on `40281c40` plus 096's share, and the **residual** is the lane's value minus the prediction.
- 037's measured values come from `wasi_python-037/build/037/p3/latest-fast.json` (746 checks, 176 with metrics, on `88e3f65`) and from `p2/latest-cpython-c-3.json` and `p2/latest-dotted-cpc.json`.
- `probes/predict.py accepted.json <lane latest.json> <those records>` prints every row with its Δ and residual.

| row kind | expected Δ against main, and whose |
|---|---|
| `test_binary_is_a_core_wasm_module[plain]` | **+43,624,926** = 037's set +43,624,918 (84,794,265; 043 +1,081,782, 037 +42,543,136) + 096's +8. Allow ±64 bytes. *(Corrected at the addendum: the first draft added 096's +8 twice.)* |
| `…[snapshot]` | **+44,024,082** = 037's set +44,024,081 (89,468,117) + 096's +1. Allow ±16 K: 096 moves no static data, but wave 02 saw wizer's 10,000-segment cap move a snapshot by about ±10 K (INFERRED). |
| `test_stdlib_zip_is_bytecode_only_and_deflated` | **+5,722,805** = 037's set +5,722,776 (44,445,916; 043 +65,005, 037 +5,657,771) + 096's +29. Expected exact: the same member bytes compress the same way. |
| any fuel row in 037's record (160 grow against main, none fall; median +3.17%) | 037's value. **Residual within ±0.05% or ±50 k, whichever is larger.** 096 changes only four `tp_clear` and one zip member, which no existing check runs. |
| the plain-start rows | +17.6 M to +19.0 M (+7.8% to +9.3%): 043's +0.43 M (19 members) plus 037's 608 members, constructors and destructors. |
| the snapshot-start rows | about +1.5 M to +1.8 M (043 +0.12 M, 037 +1.4 M to +1.6 M), and +0.22% to +0.28% on the large snapshot rows. |
| zip-walking rows (`test_the_zips_directory.py`, the resource walks) | up to +13.45% (`fast_reader…[padded]` +357 M; `resources_read_as_zipfile` +1.36 G to +1.38 G). |
| `test_upstream_suite[cpython-c]` | **+6.29%**, 375.9 G → 399.5 G (037's delta review on `40281c40`: apropos imports scipy's 95 builtins and their packages). Residual within ±0.1%. |
| `cpython-a`, `-archives`, `-b`, `-fs`, `numpy-lib` | +0.17%, +0.22%, +0.05%, +0.37% and +0.14% (037's delta review and branch run, on `40281c40`, both entries in). Residual within ±0.05 percentage points. |
| `numpy-core`, `numpy-others` and pandas groups with unchanged passes | Not measured on this set. Bound: 043's up to +0.45% plus 037's builtin-table scan. At `2687418` that was numpy-core +2.40 G (+1.18% of the old metric, about +1.5% of today's), reshape +234.6 M, io-parser +68.4 M, io-formats +55.2 M, internals +37.6 M. **numpy-core up to +2.0%; numpy-others and other pandas groups up to +0.6%.** Linux's `upstream-pandas-small` record on `95d6b217` shows those five groups' passes unchanged. |
| `pandas-frame` | **passes +73 exactly; fuel about +10.6 G (+3.1%), ±25%** (M1). |
| `pandas-groupby` | **passes +1 exactly; fuel about +8.07 G (+1.7%), ±25%** (M1). |
| fact `string-comparisons` (091) | If it moves more than 10%, I owe one sentence of cause, as 091 asks. |
| 096's five new rows | New, not ratcheted. Expect 096's measured fuel plus the new start costs: kiwi cycle about 247 M plain and 50 M snapshot; `lxml_html_diff_imports` about 720 M+ plain and 400 M+ snapshot. The slot check has no fuel. |
| 043's and 037's new rows | New, not ratcheted. 037's values are in its record: scipy dotted builtins 10.60 G plain and 10.26 G snapshot; the scipy behaviour checks 1.1 G to 5.2 G. |

**A row no claim covers** is any of these:
- a fuel row in 037's record whose residual is beyond ±0.05% (or ±50 k);
- any fuel row that **falls** by more than 0.1%;
- any passes row other than pandas-frame's +73 and pandas-groupby's +1;
- an upstream group outside its band above;
- a byte row outside its tolerance;
- a row that grows with no counterpart in 037's record, other than the upstream groups and the slow golden jobs. Slow jobs follow the plain or snapshot start plus the builtin-table scan.

Any such row stops the landing until it has a measured cause. On paper I found no existing row outside every claim.

## Constitution checks

- **§4.1 (patches).** 096's two patches each have their draft under `context/upstream/patches/` (Status: merged upstream, #245 and #477), a facts folder (28 and 29) and a CHANGELOG line. 037's three (scipy 0001 and 0002, qhull 0001) were checked by its reviews. The rules check passes. The MANIFEST hashes are the lane's build's. The main tree is clean under `recipes/`, `scripts/` and `downloads/SHA256SUMS` (EXECUTED).
- **§5.6.** Every hunk of the rebases is either `=` or named. The named hunks are README, CHANGELOG and context only, so no delta review of 096 is required beyond this one. Recipe hunks and numbers did not move.
- **§5.7.** One integration branch holds one chain (043 → 037) and one build-class fix (096). That is three build-class entries, within six.
- **§7.** No check, golden, allowance or progress file is edited to turn anything green. 096's judge changes are its own, with reasons. 037's environment entry and gap for test_pydoc are named in its `--accept-judge`.

## Accept log: pending

The lane has not yet sent its changed rows. When it does, I run `probes/predict.py` against its `build/progress/latest.json` and check each grown row against the table in criterion 4.

## Verdict

**Lands as merged at `d7fb1e6`**, on two conditions:
1. **M1:** 037's `--accept-growth` gets back its pandas-frame and pandas-groupby clause. The lane judges 043's 1%-and-passes stop condition on the residual after 037's measured share.
2. **The accept log's changed rows** each fall inside the criterion 4 table.

L1, L2 and N1 to N4 need no action to land. N1, copying 043's delta review, belongs in the reviews commit.

One line: the rebases brought only their named hunks, and the build inputs are 037's set plus 096's two patches. The slot scan finds exactly kiwisolver's four on the merged set, and its 15 skipped arrays are all pybind11's or empty. The 19 patches, 25 trees and seven gaps are right. Restore 037's pandas clause and judge 043's stop line on the residual.

## Addendum: the lane's first accept attempt, every row checked (2026-10-20)

**The attempt.** The lane judged `b325747`, which is `d7fb1e6` plus 043's delta review in `context/reviews/` (so N1 is done). It used set `a7c6b3e8` on darwin-arm64, 751 checks (`build/wave-06/latest-attempt1.json`, read only):
- 675 pass, 72 gap, 3 blocked, 1 fail;
- ratchet: lost 0, absent 0, gained 37, grew 199, more 2.

**The one failure is host litter, not a row.** `test_the_openblas_patches_are_what_their_script_makes` reported "1665 files changed, git diff names 1667". macOS wrote two `.DS_Store` files into the script's unpacked tree. 037's builder is fixing the script. The fix touches neither the set nor any metric row, so the re-accept only needs this addendum's compare repeated.

**How I checked (EXECUTED).** I ran `probes/predict.py accepted-c091f3d.json latest-attempt1.json` with 037's three records (`p3/latest-fast.json`, `p2/latest-dotted-cpc.json`, `p2/latest-cpython-c-3.json`). Output: `predict-attempt1.txt`. It gives 203 changed metric rows:
- 3 bytes rows, 196 fuel rows up and 4 down, which make 199 grew;
- 2 passes rows, which are "more 2".

Two corrections to section 4, both mine:
- The first draft added 096's bytes twice. The byte rows above are corrected.
- One row I assigned to 037's record was not in it. `cpython-c` is in it (from `latest-cpython-c-3.json`).

### Bytes: inside the table

| row | Δ against main | prediction | residual |
|---|---|---|---|
| `python.wasm` | +43,624,926 (84,794,273) | 84,794,265 + 8 | **0** |
| snapshot | +44,024,108 (89,468,144) | 89,468,117 + 1 | **+26** (tolerance ±16 K) |
| zip | +5,722,805 (44,445,945) | 44,445,916 + 29 | **0** |

The lane says `MANIFEST` gains exactly the two recipe lines and `LICENSES/` is identical. That matches N2.

### Fuel rows that 037's record measured: 161, all inside

- The residuals run from −26,540 to 0. The largest is `cpython-c`, at −0.000007%: +6.286% against the claim's +6.29%.
- Every plain row is −634 against 037's record, and every snapshot row is −2. This is a constant shift in the start cost, far inside ±50 k.
- The zip-walking rows sit at +10.5% to +13.45% (`fast_reader…[padded]` +357.19 M, `resources_read_as_zipfile[plain]` +1.378 G), as the table says.
- 037's new rows (scipy behaviour checks, scipy dotted builtins) equal its record to within 634 fuel.

### The 44 rows no record measured: all inside the bands

**Upstream groups:**

| group | Δ | band |
|---|---|---|
| `cpython-a` | +0.173% | +0.17% |
| `cpython-archives` | +0.221% | +0.22% |
| `cpython-b` | +0.052% | +0.05% |
| `cpython-fs` | +0.375% | +0.37% |
| `numpy-lib` | +0.138% | +0.14% |
| `numpy-core` | +0.127% (+0.198 G) | at most +2.0% |
| `numpy-others` | +0.087% | at most +0.6% |
| `pandas-internals` | +0.180% | at most +0.6% |
| `pandas-libs` | +0.164% | at most +0.6% |
| **`pandas-frame`** | **+73 passes, +10.23 G (+2.97%)** | +73 exactly; ~+10.6 G ±25% (here −3.5%) |
| **`pandas-groupby`** | **+1 pass, +7.31 G (+1.52%)** | +1 exactly; ~+8.07 G ±25% (here −9.5%) |
| `pandas-io-formats` | −0.026% | a fall within 0.1% |
| `pandas-io-parser` | −0.003% | a fall within 0.1% |
| `pandas-reshape` | −0.007% | a fall within 0.1% |
| `pandas-tslibs` | −0.034% | a fall within 0.1% |

The four pandas rows that fell are the only rows that fell. None falls by more than 0.1%.

**What these numbers mean:**
- numpy-core's growth is far below the old toolchain's +1.18%. 043's 1% stop line is not crossed by any group except cpython-c, pandas-frame and pandas-groupby. Each of those three is 037's measured share (M1).
- The fact `string-comparisons` is 58,508,224,627. That is −0.9% against 091's quoted 59.05 G, inside the 53.1 G to 65.0 G band, so no sentence is owed.
- numpy-core's passes stay 9,519.

**Slow golden jobs and other rows (27 of them):**
- Plain rows: +18.3 M to +63.6 M (+0.31% to +1.11%; +2.86% and +3.48% only on the small regex and patched-callbacks bases).
- Snapshot rows: +2.1 M to +13.2 M.
- Each is the plain start's +18.9 M (or the snapshot's +1.5 M to +1.8 M) plus the builtin-table scan of its missed imports. That is 037's claim ("the long golden jobs").
- The largest are `test_encodings_are_wasi_libcs_as_documented` +174.2 M (+0.57%) and `test_lxml_xml_job_matches_native` +121.6 M (+0.51%).

### New rows (not ratcheted)

**096's four fuel rows:**

| row | measured | expected |
|---|---|---|
| kiwi cycle, plain | 247,066,429 | about 247 M |
| kiwi cycle, snapshot | 49,927,505 | about 50 M |
| `lxml_html_diff_imports`, plain | 720,947,666 | 720 M+ |
| `lxml_html_diff_imports`, snapshot | 401,531,991 | 400 M+ |

**Check 3** passes on the wave set with 554 types, 461 specs, 246 module definitions and 5,893 functions. These are the same numbers as on 037's set, now with no finding. The record's reason is cut at "67 specs with slots past the image," as L2 says.

**Others:**
- 043's two gaps now pass: `test_contour_runs` and `test_delaunay_triangulation_runs`.
- 037's seven gaps hold as gaps.
- Blocked: `test_wheel_carries_the_artifact_set` and `test_same_bytes_passed_on_three_systems` (both are blocked on this host) and one prior-art check.
- No check is gone.

### Verdict on the attempt

**No row falls outside the section-4 table.** Every grown, fallen and moved row has its measured cause, and the fail is host litter in one script's work tree.

After 037's script fix:
- The re-accept needs only a repeat of this compare.
- The set (`a7c6b3e8`) and every metric row should be identical. The script check should pass.
- Any other difference is a finding.

M1's accept text still applies: restore 037's pandas clause, and judge 043's stop line on the residual. With that, the wave **lands as merged** (now `b325747` plus the script fix, with a delta look at that fix's diff).

## Addendum 2: delta look at 037's litter fix (`git diff 40f30cd 2f441db`), 2026-10-20

**Reviewed:** `wave/06` at `d066695`. The chain is now `40f30cd`, then 037's `2f441db` (the fix), then 096 replayed (`0e6ee93`), then the reviews commit.

**What moved besides the fix (EXECUTED):**
- `git range-diff 40f30cd..d7fb1e6 2f441db..0e6ee93` shows all twelve 096 commits as `=`.
- `git diff d7fb1e6 d066695` touches four files:
  - the fix's three: the script, the unit row, and 037's spec note;
  - 043's delta review, added by the reviews commit.

**The fix (READ):**
- `scripts/make_openblas_void_patch.sh` now checks the pinned tarball's listing first. If any path part is litter by `scripts/litter.py`'s `has_litter` (the OS names, and AppleDouble `._` files), the script stops.
- After each `git add -A --force`, it then removes every staged litter path from the index with `git rm --cached`. The files stay where they are.
- An untracked file appears in no `git diff`, so litter is in neither the pristine commit, the count nor the patches.
- The script runs under `set -eu`.

**Does it hide a real file? No. It fails closed both ways:**
1. **Nothing from the tarball can be unstaged.** The script stops before `git init` if any tarball path holds a litter part. The pin is a SHA-256, so the listing cannot change without a pin move. The builder ran this against OpenBLAS 0.3.34's tarball and found no litter name.
2. **A litter-named file the converter itself made would be caught.** It would be unstaged, so it would leave the count but not `files changed:`. The existing `[ "$said" = "$counted" ]` comparison would then stop the script. Hiding such a file turns the check red; it does not turn it green.
3. **One edge only (N5, negligible).** `tar -t` may print a control character escaped. So a tarball member named `Icon\r` might escape the listing check and later be unstaged. OpenBLAS 0.3.34 has no such member, and a pin move re-runs the check.

**The unit row** is `test_the_openblas_patch_script_counts_no_host_litter`, in `tests/unit/test_scipy_build.py`.
- It plants `.DS_Store`, `lapack-netlib/.DS_Store` and `._sgesv.c` between the two adds, with a stand-in tarball and convention script.
- It asserts the three real files are named, and that no `DS_Store` reaches a patch.
- The builder saw it fail first on the old script (3 said, 6 counted).
- `ruff check` and `ruff format --check` on it are clean (EXECUTED). I ran no pytest: the lock is held.

**For the lane:**
- `tests/unit/test_scipy_build.py` is now a changed judge file. Add the row to 037's `--accept-judge` text ("the patch script counts no host litter: one unit row").
- The set's bytes are unchanged. `SHA256SUMS` is `f12cd25c`, and `MANIFEST` moves only in the script's `recipe` line.
- No growth claim changes.

**Expected in attempt 2, against attempt 1:**
- `test_the_openblas_patches_are_what_their_script_makes` changes from fail to pass.
- One new unit row.
- Every metric row identical. Fuel is deterministic, as attempt 1's residuals show.
- Any other difference is a finding.

**Verdict unchanged:** lands as merged, now at `d066695`, with M1's accept text.
