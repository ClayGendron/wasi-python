# Review of 166 — The pins move for 0.1.3 (the second pull request: pandas 3.1.0 and zlib 1.3.2)

- **Date:** 2026-10-31
- **Reviewer:** an agent (Claude Opus 5.5), a fresh sub-agent of the orchestrating session; not the author
- **Reviewed:** `30566232..2db34a1e` on `spec/166-pandas-3-1-0` (13 commits, rebased onto `dev` after #67 merged), then each round to the head `aedf53ed` (on `dev` at `a0f3e3b5`; rounds 1 to 4 below), with the specification, the owner's decisions of 2026-10-31 (`context/decisions.md:537-539`), and the worktree's rebuilt set
- **Run:** 41253971237 on `aedf53ed` (round 4). Every judge leg is green. `review` and `ci-status` fail only because this file is not yet committed. I read it myself with `gh pr checks 71`: 66 pass, 13 skipped, and 2 fail, `review` and `ci-status`. Before it, 41209090235 ran on `bc605abf`, the head after the rebase onto 165's merge; it was red only in tqdm-smoke's classes. I read its `release-assets` as the author saved them locally; I made no `gh` call.
- **Re-ran (all EXECUTED, `WASI_PYTHON_ARTIFACTS` set to the worktree's set, `-n 2`):**
  - The fast tier, `tests/unit`, `tests/lint`, `test_rules.py` and `test_upstream_files_are_well_formed`: 3,648 passed. One row is blocked by the prior-art clones, as on `dev`.
  - `test_upstream_suite[pandas-io-parser]` with its two classes: 2 passed and 1 xfailed (the no-mmap gap). Fuel was 94.3 G before and 182.2 G now, under the 261 G cap.
  - `--tier release`, `scikit-learn-datasets` and `statsmodels-tsa-statespace-2` with their new classes: 2 passed and 2 xfailed. Passes fell 356 → 329 and 591 → 590, exactly as the release ledger claims. The local ratchet calls these falls red because it does not read the ledger.
- **Time box:** 45 minutes (build-class); exceeded by the native runs.

Labels: EXECUTED means I ran it; READ means I read the file cited; INFERRED means my reasoning.

## Acceptance criteria against evidence

1. **Pins.** Both new tarballs match their publishers (EXECUTED). `pandas-3.1.0.tar.gz` (`ecb9b2d8…`) matches PyPI's `digests.sha256`. `zlib-1.3.2.tar.gz` (`bb329a0a…`) matches the v1.3.2 release asset's GitHub `digest`. Every `recipe` line in the set's `MANIFEST` equals its file at the head, and every file in the set checks against `SHA256SUMS` (EXECUTED).
2. **The patch.** The Styler patch's `+`, `-` and `@@` lines equal those of 3.0.6's patch; only the `index` line differs. It applies to a fresh 3.1.0 tree with no offset (EXECUTED).
3. **`XSIMD_WITH_EMULATED=1`: correct and safe.**
   - On wasm32, pandas' meson picks `moments_scalar.cpp` (`pandas/_libs/simd/meson.build`). That file specialises `accumulate_mean<xsimd::common>` and calls no batch code. The shared header `moments_simd.hpp` still names `xsimd::batch`.
   - Without the flag, a target with no SIMD hits `XSIMD_NO_SUPPORTED_ARCHITECTURE` (`xsimd_config.hpp:605`). With it, xsimd declares that API through its emulated architecture, which is plain scalar code.
   - No SIMD is turned on, and the guest stays without SIMD128 (READ).
4. **`-Dfast_float=pandas_fast_float`: no change in behaviour.**
   - The macro only renames the namespace token. It leaves alone `#include "fast_float/…"` (a header name is not macro-expanded), string literals, and other identifiers such as `fast_float_strtod`.
   - pandas' archives hold 19 `pandas_fast_float::` symbols and no `fast_float::` symbols (EXECUTED, `llvm-nm`). So pandas' fast_float 8.2.10 and scipy's older single-header copy no longer share weak names that the linker would pick between arbitrarily. That makes the rename a correctness fix, not a cosmetic one.
5. **The 41 recorded failures: verified natively, each one.** I ran them under the oracle's native pandas 3.1.0, scikit-learn 1.9.1 and statsmodels 0.15.0, with pytest beside it (EXECUTED).
   - scikit-learn's `test_openml.py`: exactly the 27 listed nodes fail. A `diff` of the native list against `pandas-categories.txt` is empty, and the error is `TypeError: expected string or bytes-like object, got 'int'`.
   - statsmodels, under the judge's own `tests/upstream/statsmodels.ini`: the 12 concentrated-initialization tests error, and `test_plot_quarter` and `test_news_summary_methods` fail. All 14 fail on `Pandas4Warning: The inplace keyword in DataFrame.set_index is deprecated`.
   - Each class's member list is fixed by its digest, so a class hides nothing beyond its listed members.
6. **pandas' own new classes, beyond the 41.**
   - `pandas-io-parser/no-mmap` gains 17 members: 16 tests in the new `test_parallel_read.py`, and `test_memory_map_multichar_sep[python]`, which is new in 3.1.0 and absent from 3.0.6. It passes `memory_map=True`.
   - `pandas-slow-b/no-mmap` has 9 members, all in the new file.
   - `pandas-slow-b/wasm32-int32` has 3 members, the cases of `test_categorical_dtype_high_cardinality_numeric`. 3.1.0 rewrote that test so that it builds its expected categories from `np.array` of Python ints. I confirmed the class's cause in the guest (EXECUTED): `read_csv(dtype="category")` infers `int64` categories, as native pandas does, while `np.array([1]).dtype` is `int32`.
   - These three cases passed under 3.0.6 and are not among the owner's 41 (Low 4).
7. **io-parser's cap: within its tier's rules.**
   - pandas' groups are normal-tier path groups. The 100 G bound applies only to smoke groups (`packages.py:1478`), and `test_upstream_files_are_well_formed` passes.
   - The cap keeps the former headroom: 261 / 182.2 = 1.432, against 135 / 94.3 = 1.432.
   - The fuel grew 93%, past Decision 11's +15% per pandas group, and the cause is traced: the new `test_parallel_read.py` (79.7 G) and 1,311 more passing tests. The growth is claimed.
8. **Bytes and the wheel.**
   - `python.wasm` is 100,633,998 bytes and the zip 54,162,674 (EXECUTED). Against the first pull request's set, the landing notes give +1.146% and +0.620%, within +3%.
   - The wheel, built by hand at the head, is 99,207,558 bytes (READ), under the line the owner set on 2026-10-31, 104,857,600.
9. **Same bytes at the final head: not yet shown** (Medium 1).
10. **Licences.**
    - `LICENSES/pandas.txt` ships pandas' new `NERI_SCHNEIDER_LICENSE`, `STATSBASE_JL_LICENSE` and `XSIMD_LICENSE`, and fast_float's `LICENSE-APACHE`, `-BOOST` and `-MIT`. The owner approved them on 2026-10-31 (READ).
    - zlib's `LICENSE` changes its years only. `minizip`, which gains a new licence file, is not built (READ).
11. **The news file.**
    - The claim block is this pull request's alone. The Security line for zlib follows 1.3.2's ChangeLog (READ).
    - `pandas.ini` is a faithful transcription: 3.1.0's own list begins with `error` (`pyproject.toml:462`), and the one ignore the driver adds carries its reason.
    - The commit trailers name Claude Opus 5.5 on all 13 commits (EXECUTED).

## Findings, most severe first

1. **Medium: the set at the final head has no cross-host comparison yet** (Decision 12; landing notes, "Decision 12"). The landing notes compare `SHA256SUMS` digest `91105cf5…` with run 41180751848's arm64 Linux set at `c3927750`. That was before zlib 1.3.2 and before the rebase, whose changes from 162 and 164 rebuilt steps 60 to 90. The set at `2db34a1e` has `SHA256SUMS` digest `e5c1100eb94dc54de…`, `python.wasm` of 100,633,998 bytes (EXECUTED), and no other host has voted on it. Failure: a host-dependent byte in zlib 1.3.2's build, or in the rebuilt reactor, would reach `dev` unseen until the weekly run. Evidence that closes it: the run on `2db34a1e` builds its arm64 Linux set, and its `SHA256SUMS` is byte-identical to the worktree's `build/artifacts/SHA256SUMS` (digest `e5c1100eb94dc54de36631932618ceacb0ccfab7c92b0d1aebeb777c4defc79d`). Record that sentence in the landing notes.

2. **Medium: nothing holds that a large CSV is read serially in the guest** (`build/pandas-3.1.0/pandas/io/parsers/readers.py:400-420, 432-455`).
   - pandas 3.1.0's `read_csv` takes a parallel path by itself when a local file is 5 MB or larger and `_default_n_workers() > 1`. That path maps the file. The check that would stop it, `sys.platform == "emscripten"`, does not cover WASI.
   - Today it is safe only because the guest's `os.cpu_count()` returns 1. I confirmed that (EXECUTED): the default reads a 7,266,676-byte file serially and returns its 400,000 rows. But with `pd.set_option("mode.max_threads", 2)` the same call raises `OSError: mmap is unavailable on wasm32-wasi`. That error is not one the parallel path catches before it falls back.
   - Failure: if a wasi-libc or CPython change ever reports more than one CPU, every `read_csv` of a file of 5 MB or more raises, and no check would see it. pandas' own `test_read_csv_auto_parallel` forces `max_threads=4`, so it tests the opt-in, not the default.
   - Fix: add a check to `tests/checks/test_v1_3_data_stack.py`. It writes a CSV of 5 MB or more under a writable root, then asserts two things: `read_csv` with pandas' defaults returns every row, and with `mode.max_threads` set to 2 it raises `OSError`. Add one sentence to the "No `mmap`" bullet of `docs/reference/limitations.md`: "pandas' parallel `read_csv`, chosen by setting `mode.max_threads` above 1, maps its file and raises `OSError`; leave the option unset."

3. **Low: the news file's growth text gives the superseded numbers** (`context/changes/166-the-pins-move-for-0-1-3.md`, the `growth` key). It quotes the wheel at 99,186,606 bytes, "813,394 under 100,000,000", and byte changes measured at `c3927750`, before zlib and the rebase. Fix: give the head's figures: `python.wasm` 100,633,998 bytes, the snapshot 105,737,136, the zip 54,162,674, the wheel 99,207,558 bytes, 5,650,042 under PyPI's 104,857,600 (the owner's line of 2026-10-31). Each is measured against the first pull request's set and labelled as such.

4. **Low: three passes fall beyond the owner's 41, and the notes should say so** (`tests/upstream/expected/pandas-slow-b/wasm32-int32.txt`; the release ledger's `fewer`). The ledger gives the reason for the three `test_categorical_dtype_high_cardinality_numeric` cases, and criterion 6 confirms the cause in the guest. The test was rewritten upstream, and its expectation depends on the platform; the guest's own answer is native's. This is the documented 32-bit default integer, the same kind of gap as the existing ones, so it needs no owner. Fix: one sentence in the landing notes: "Beyond the owner's 41, pandas-slow-b loses three passes of a test 3.1.0 rewrote: its expected categories take numpy's 32-bit default integer, while the guest's read_csv infers int64 categories as natively (class wasm32-int32, closed by limitations.md)."

5. **Note, no action needed: on the local scoreboard, io-parser's growth is claimed by 162's news file**, whose broad `grows` pattern comes first. 166's own `tests/checks/*` covers it too.

6. **Note, read and sound: `07c6cd18`, jinja2-r's two asyncio classes** (local, after `2db34a1e`). Under CPython 3.15.2, the stray event loops of jinja2's async tests are collected at other moments, so the members trade between the classes. The failed class goes from 104 to 106 members and the teardown-error class stays at 13. The new members carry the same cause, matched by the same patterns as before (`[Errno 58] Not supported|unraisable exception warnings|Exception ignored while calling deallocator`). This is the kind of trade I accepted for tqdm in #67's round 1. I re-ran the suite and its two classes with `--tier release`: 1 passed and 2 xfailed, with no FEWER line, so jinja2-r's pass count holds (EXECUTED). The news file claims both expected-lists and `known_gaps.toml` under `[claim.judge]`, and the ledger's block is extended. No action is needed.

## Constitution checks

- **§4.1:** holds. One patch is re-made with the same changed lines, its draft moved, and the news file names it by path. Both cross-file flags are recipe files, not patches.
- **§4.2 (pins):** holds; see criterion 1.
- **§4.12:** holds. The new notices ship and the owner approved them; zlib's year change was approved.
- **§5.6:** this is a change to the build recipe, under 166's pre-build review. The C++20 path (Decision 8, option A) took recipe-first adaptations only.
- **§7:** no judge file was edited to turn a run green. Every new class is a cause verified natively or in the guest; each has its closer and its fall claimed.
- **Structure:** nothing under `src/` changes.

## Disposition (filled in by the author, then confirmed by the reviewer)

The round's fix commit is `305bdb03`. The branch was rebased onto `dev`'s acceptance commit `a88e9ec5`, which changes only `context/progress/`, and it carries the jinja2 commit as `3e4898b2`. Nothing the set reads changed, so the worktree's set still stands for this head. The fix commit touches no recipe file, `scripts/` or `src/` (READ, `git diff --stat 2db34a1e 305bdb03`).

1. Medium 1 — closed by run 41209090235 on `bc605abf`. I checked its `release-assets`, which the author saved under `build/166/ci-assets2/` (EXECUTED):
   - The set's `SHA256SUMS` hashes to `bf4ba357239a44933fa9e7585bfffb300c0fc40cf6555ec70402cd43f7534ea6` and is byte-identical (`cmp`) to the worktree's `build/artifacts/SHA256SUMS`.
   - Every file of the run's set checks against it, with 0 mismatches.
   - The run's wheel is 100,341,646 bytes, the same as the one built by hand.
   - That this set is the arm64 Linux build is the author's statement; I did not read the run.
   - Reviewer: confirmed. Writing this sentence into the landing notes may wait for the next commit that touches `context/` only.
2. Medium 2 — fixed in `305bdb03`. The new `test_a_large_csv_is_read_serially` writes a 5.5 MB CSV in the guest and asserts that the default `read_csv` returns 250,000 rows. It also asserts that `mode.max_threads=2` raises `OSError`, and that `limitations.md` names the option. The limitations sentence is the one this review gave. Reviewer: confirmed (EXECUTED).
   - The check passes on the worktree's set, together with `tests/lint` and `test_rules.py` (149 passed, 1 skipped), and `ruff` is clean.
   - The check would catch the regression it guards. With `os.cpu_count` patched to return 2 in the guest, the default read of the same file raises `OSError: mmap is unavailable on wasm32-wasi`.
3. Low 3 — fixed in `305bdb03`. The growth text gives this head's figures, measured against the first pull request's set. Reviewer: confirmed (READ).
4. Low 4 — fixed in `305bdb03`. The ledger's `fewer` names the three cases "beyond the owner's 41", with their cause. Reviewer: confirmed (READ).
5. Note 6 (jinja2-r) — the commit is now `3e4898b2`, with the same content. The coordinator's growth claim for the markup job rides in `305bdb03` under `grows`. Reviewer: read.

**The rebase onto `dev` at `28a1e7cf`, the merge of 165 (#70); the head is now `bc605abf`.**
- `git range-diff` shows only two changes. The release ledger now keeps 165's block beside this one, which is a conflict resolution. And `bc605abf` updates the figures in the news file and the landing notes. Every other commit is unchanged (READ).
- The set was rebuilt from steps 00, 70, 80 and 90 for 165's pins and snapshot list (EXECUTED on the worktree's set):
  - `python.wasm` is unchanged at 100,633,998 bytes. The snapshot is 105,807,351 bytes and the zip 55,293,519.
  - `SHA256SUMS` hashes to `bf4ba357…`, every file checks against it, and every `recipe` line in `MANIFEST` equals its file at `bc605abf`.
- The wheel is 100,341,646 bytes. That is past decision 64's 100,000,000, but 4,515,954 under 104,857,600, the line the owner set on 2026-10-31 until PyPI raises the limit. The owner's decision foresaw this: "With 165 and pandas 3.1.0 the wheel is about 100.3 MB".
- The author reports lint and the fast tier green at this head (3,648 passed).

**Round 2: `314150a8`, tqdm-smoke's classes trade back.** Run 41209090235 was red only in tqdm-smoke's three classes.
- With pandas 3.1.0 and zlib 1.3.2 in the set, `test_iter_basic_overhead` and `test_iter_overhead_simplebar_hard` trade back between the classes. This is the swap #67 recorded, run in reverse.
- The three expected-lists are now byte for byte what they were before 166 (`git diff a1acec5c 314150a8` is empty for all three). The gaps return to their old digests: `ca9d96e202af`, `10c256abd391` and `c5948e42a741`. Each moved test keeps its class's cause and pattern, as I found in #67's round 1.
- I re-ran `test_upstream_suite[tqdm-smoke]` and its three class checks on the worktree's set: 1 passed and 3 xfailed, with no FEWER line (EXECUTED).
- The news file claims the three checks under `changed` and the three files under `[claim.judge]`.
- Note: these two `tests_perf.py` tests flip whenever the set's allocation pattern moves, because the moment the stray event loop is collected moves with it. That is the second flip in one day. The author found (2026-10-31) that the present harness cannot hold both states. A class that matches on its reason would also take about 200 failures across `tests_tqdm.py`, and a class with one outcome only lists its nodes. The narrowest fix is a change to the harness: a class that names its nodes and accepts both outcomes. That would be its own specification; it does not hold this pull request.

**Round 3: the rebase onto `dev` at `a0f3e3b5` (171, with 167's pdfplumber and xarray beneath it); the head is `49f1dd04`.**
- **The rebase itself:** `git range-diff` shows only three resolved conflicts, plus `49f1dd04`, which records the figures. The first is step 70's metadata line, which takes 171's `…/pandas-3.1.0/PKG-INFO=pandas` form. The second is the oracle's lock, which keeps 167's pins. The third is the gap file's and the ledger's neighbours. Every other commit is unchanged (READ).
- **The rebuilt set** (EXECUTED): `SHA256SUMS` hashes to `61a676db7989be8a3e6ab7f56769b8e316c2ec1dece027722f9ec9603f2fe68a` and every file checks against it. Every `recipe` line equals its file at `49f1dd04`. `MANIFEST` names pandas 3.1.0 and zlib 1.3.2.
- **Sizes:** `python.wasm` is 100,638,734 bytes, the snapshot 106,033,650 and the zip 57,402,013. The author reports the wheel at 102,521,515 bytes, under the owner's 104,857,600.
- **No 3.0.6 left:** no tracked file outside the unit tests' synthetic fixtures names pandas 3.0.6, except one gap reason (Low 8).
- **xarray, which arrived on `dev` after this pull request was built and is a heavy pandas dependent:** I ran all its groups on this set. That needed pytz 2026.6, a test-only wheel this worktree's `build/upstream/wheels/` lacked. I copied it from the 167 worktree after checking its SHA-256 against `tests/upstream/kit-extra.txt` (`7fed3fee…`). That is the only file I wrote outside the review. Results: `xarray-smoke` 1 passed; `--tier release -k xarray-r`: 7 groups passed, 10 class gaps held, 1 failed (EXECUTED, 26 minutes).

7. **Medium (new): pandas 3.1.0 costs `xarray-r-rest` an accepted pass, and nothing records it** (`tests/upstream/xarray.toml`, group `xarray-r-rest`).
   - `xarray/tests/test_indexes.py::TestPandasMultiIndex::test_sel` now fails in the guest with `KeyError: 'Key length (3) exceeds index depth (2)'`.
   - It fails the same way on native pandas 3.1.0 with xarray 2026.9.0, run from this worktree's xarray tree under the oracle's interpreter (EXECUTED). So it is a known upstream failure of the same kind as the owner's 41.
   - It is not one of those 41. The owner's answer of 2026-10-31 predates xarray on `dev` and names scikit-learn's and statsmodels' tests only.
   - Failure: the release tier loses an accepted pass in `xarray-r-rest`, unclaimed. The weekly run or the release pull request goes red on it.
   - Fix:
     - A class `pandas-multiindex-sel` in `xarray-r-rest` (outcome `failed`, match `Key length \(3\) exceeds index depth \(2\)`, reason "pandas 3.1.0's MultiIndex.get_loc raises KeyError for a key longer than the index's depth where xarray 2026.9.0's test expects its own error; the same natively", closer `context/roadmap.md`).
     - Its expected-list file with that one node, its gap in `known_gaps.toml`, and the fall in the release ledger's `fewer`.
     - A line in the roadmap's reserved entry naming xarray's next release.
   - **This one needs the owner's word.** The owner's decision covers 41 named tests. The orchestrator asks with AskUserQuestion: **A** (recommended): record it like the 41; **B**: hold pandas 3.1.0.
8. **Low (new): an xarray gap's reason names pandas 3.0.6** (`tests/known_gaps.toml`, `xarray-r-dataset-fails-natively`). The gap holds at 3.1.0: `TestDataset::test_repr` fails natively on pandas 3.1.0 too (EXECUTED). Fix: change its reason's "pandas 3.0.6" to "pandas 3.1.0".
9. **Medium 1 reopens for the new set.** The run on `49f1dd04` must build an arm64 Linux set whose `SHA256SUMS` is byte-identical to `61a676db7989be8a3e6ab7f56769b8e316c2ec1dece027722f9ec9603f2fe68a`.

**Round 4: `aedf53ed`.**

- **Medium 7, fixed.** Reviewer: confirmed.
  - The class `pandas-multiindex-sel` is in `xarray-r-rest`, with outcome `failed` and the match `Key length \(3\) exceeds index depth \(2\)`. It has its reason and its closer, `context/roadmap.md`, whose entry names xarray's next release after 2026.9.0. Its expected list holds the one node. Its gap counts 1 finding, digest `b79efce58684`. The release ledger's `fewer` claims the fall.
  - The owner's answer (A, record it like the 41) is in `context/decisions.md` (READ).
  - I re-ran on the set, with `--tier release`: `test_upstream_suite[xarray-r-rest]`, its new class, `xarray-r-dataset` and that group's `fails-natively` class. Result: 2 passed and 2 xfailed (EXECUTED).
- **Low 8, fixed.** The gap's reason now names pandas 3.1.0, which my native run backs. Reviewer: confirmed.
- **No recipe file, `scripts/`, `src/` or download changed** (`git diff --stat 49f1dd04 aedf53ed`), so the set is still `61a676db…`.
- **Medium 1, closed again, by run 41253971237 on `aedf53ed`.** Reviewer: confirmed. I checked its `release-assets`, saved under `build/166/ci-assets3/` (EXECUTED):
  - The set's `SHA256SUMS` hashes to `61a676db7989be8a3e6ab7f56769b8e316c2ec1dece027722f9ec9603f2fe68a` and is byte-identical (`cmp`) to the worktree's.
  - Every file of the run's set checks against it, with 0 mismatches.
  - The run's wheel is 102,521,515 bytes, under 104,857,600.
  - That this set is the arm64 Linux build is the author's statement; I did not read the run.

## Verdict

Lands on aedf53ed: nothing ranked High or Medium stands, run 41253971237's judge legs are green, and its arm64 Linux set is byte-identical to the worktree's.
