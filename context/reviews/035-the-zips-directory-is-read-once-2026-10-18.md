# Review of 035 — The zip's directory is read once (the build)

- **Date:** 2026-10-18
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change, the specification, its pre-build review or its confirmation. I read `AGENTS.md`, the constitution (§4, §7), `context/README.md`, the review template, `context/progress/README.md`, specification 035 as it stands in the worktree (Decisions, Design, Acceptance, landing notes), its pre-build review with its Disposition and Confirmation, spec 051 (whose callback scan binds this build), the owner's decisions 57–63 on main (`2d7a0ae`), and the whole diff. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `spec/035-the-zips-directory-is-read-once` in `../wasi_python-035`: `c6900b6` (part 1), `749b873` (part 2), `0a875e1` (part 3), `ca2ecc3` (README, CHANGELOG, upstream draft, landing notes). `git diff main...HEAD`: 18 files, +1,838 −31. The branch is one commit behind main; that commit (`2d7a0ae`) touches only `context/`. The worktree's own `build/artifacts/` (`python.wasm c2e7c88f…`, `python-snapshot.wasm 2993fb91…`, `python-stdlib.zip daf2cdd8…`, `MANIFEST b973b33e…`), against main's `build/artifacts/` (051's set: `5648e4c5…`, `f94dec53…`, the same zip, `MANIFEST c4474f76…`).
- **Edited nothing in either tree.** My scripts and copies are in this review's folder (`$R` = `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/5c4a788f-6229-4fb4-8a87-05b4e7e5e695/scratchpad/035-buildreview/`); my logs are under the worktree's ignored `build/review035/`. Mutants were applied to a `git archive` copy of HEAD (`$R/mut/`), never to the worktree, and restored from byte copies (`cmp` clean). A subset judge run rewrote `build/progress/latest.json`; I put back the copy from my full run. I rebuilt the worktree's artifacts with `scripts/build.sh` (below); that rewrites ignored files under `build/` only. Every command went through `uv run`, or ran a build script.
- **Re-ran:** see "What I ran". The full judge: `1211 passed, 10 skipped`; scoreboard `271/274 pass · 0 gap · 3 blocked · 0 fail`; ratchet `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 20 · grew 4`; exit 1 (`RED: 4 metric(s) grew`, the accept's growth list).

## What I ran (EXECUTED unless labelled)

- **The full judge**, `uv run pytest` (slow included, no `--accept`) in the worktree on its own artifacts → `build/review035/judge-full.log`. Plus `ruff check` and `ruff format --check` on `src tests`, and on the new recipe and script files.
- **Every metric against the accepted state** (`$R/ratchet.py`, `build/review035/ratchet.txt`): latest.json against `context/progress/accepted.json` (darwin-arm64).
- **Fail-first**: the new check file run against main's artifacts (`WASI_PYTHON_ARTIFACTS=<main>/build/artifacts`) → `build/review035/failfirst.log`.
- **The landing notes' numbers**, on both sets, with the judge's driver (`$R/measure.py` → `build/review035/measure.log`).
- **The growth on `test_extra_preopens_work_on_the_snapshot`**, split into setup, a plain loop and two `isinstance` loops on both snapshots (`$R/growth.py` → `build/review035/growth.log`).
- **A differential fuzz of the directory reader on the host** (`$R/fuzz_reader.py`): HEAD's `recipes/zip_directory.py` against CPython 3.15.0's own `zipimport._read_directory`, loaded from the pinned source in `build/Python-3.15.0/Lib/zipimport.py`, on 30,000 zips: random ordinary zips (odd names, duplicates, comments, extras, prepended bytes), 85% of them corrupted in the directory and end record (byte flips, end-record fields set to 0, 1, 2, max or random, cuts, inserted signatures).
- **The same comparison in the guest**, on both sets (`$R/probe_guest.py` → `build/review035/probe.log`): `read_directory` against `stock_read_directory` on 156 zips (six crafted hostile ones and 150 corrupted ones), and 30 resource and metadata probes compared between main's binaries and 035's (`as_file`, `contents`, `is_resource`, `read_text`, `pkgutil.get_data`, `available_timezones`, `distributions`, `packages_distributions`, `locate_file`, a prefixed zip on `sys.path`, and others).
- **A zip rewritten in place** after its first read, on both sets (`$R/stale.py` → `build/review035/stale.log`).
- **22 mutants** of the two recipe modules (`$R/mutate.py`), each against `tests/unit/test_zip_directory.py` and, for the reader's, the fuzz above (6,000 zips each).
- **Each intermediate commit** (`git archive` of `c6900b6`, `749b873`, `0a875e1`): `ruff check`, `ruff format --check`, `pytest tests/unit`.
- **A full rebuild from pins** in the worktree, `scripts/build.sh --plain` → `build/review035/build.log`, and its `SHA256SUMS` against the one I saved first.
- READ: CPython 3.15.0's `zipimport.py` (`_read_directory`, `_get_files`, `get_resource_reader`), `_bootstrap_external._path_join`, `importlib/resources/readers.py` (`ZipReader`), `importlib/resources/abc.py` (`Traversable` is a `runtime_checkable` `Protocol`), `zipfile/_path/__init__.py` (`Path`), `importlib/metadata/__init__.py` (`FastPath`), `Python/import.c` (`look_up_frozen`: bootstrap table, then `PyImport_FrozenModules`), `Python/sysmodule.c` (`_PySys_SetPreliminaryStderr`, so `PyErr_Print` between the phases has a stderr).

## The judge (EXECUTED, `build/review035/judge-full.log`)

`1211 passed, 10 skipped in 265.64s`. `wasi_python v1: 271/274 pass · 0 gap · 3 blocked · 0 fail (unit suite 940/947, 7 skipped)`; v1.3 47/47. Blocked: `prior-art clones`, `three systems`, `wheel`, as on main. Ratchet against `614520fff6`: `lost 0 · absent 0 · unrun 0 · unrun locally 1 · gained 20 · grew 4`. The "unrun locally" is the prior-art licence check: the worktree has no clones, as for 051's review. The landing notes say "Lost 0; gained 20", which holds; they do not mention the one unrun-locally check. `test_callbacks_have_the_types_cpython_calls` (051's scan) passes. `ruff check` and `ruff format --check` are clean on `src tests` (71 files).

The judge prints only three `GREW` lines (`scoreboard.py:351` caps them). The fourth, from my comparison, is `[root first]`. The four are exactly the landing notes' list:

| check | metric | before | after | growth |
|---|---|---|---|---|
| `test_binary_is_a_core_wasm_module[plain]` | bytes | 31,760,992 | 31,786,310 | +25,318 (+0.080%) |
| `test_binary_is_a_core_wasm_module[snapshot]` | bytes | 65,533,118 | 65,552,587 | +19,469 (+0.030%) |
| `test_extra_preopens_work_on_the_snapshot[root first]` | fuel | 847,440,276 | 848,343,152 | +902,876 (+0.1065%) |
| `test_extra_preopens_work_on_the_snapshot[data first]` | fuel | 847,440,410 | 848,343,286 | +902,876 (+0.1065%) |

53 metrics fell: every plain check by about 88 M to 94 M (three resource-heavy ones by 215 M to 657 M), snapshot checks by 3,450 to 507,441. No plain check grew; the snapshot `-c pass` fell 0.2%. Decision 10's two red lines are not crossed.

## Acceptance criteria against evidence

1. **The gate, both binaries** — met. EXECUTED: passes in the full run; `served == {zip: "fast"}`, `encodings` from a `zipimporter`, the three seams ours, origin `frozen`, `zipimport.__file__` and `loader_state.filename` as a one-phase start gives them. It fails on main's set (`failfirst.log`). Install point A serves; B was not built (READ, the C diff).
2. **Plain start slope ≤ 30,000** — met. EXECUTED: 25,058 per member (small.zip 151,061,223, padded.zip 283,365,243). Fails on main's set.
3. **The fast reader builds zipimport's dict** — met, with the builder's two readings, which I accept. EXECUTED: all eight cases pass, and fail on main's set. The truncated zip is `"stock"` by Decision 2's routing and raises `EOFError` from both readers; the stricter "walk ends exactly at `cd_size`" is in the safe direction (my fuzz below agrees). Beyond the criterion: 0 differences between the reader and 3.15.0's own on 30,000 host zips (9,850 served fast) and on 156 zips in the guest (76 fast, 80 stock), including a bad local-header offset, a negative archive offset, a Zip64-extra entry without a Zip64 end record, an invalid UTF-8 name under the UTF-8 flag, odd names, and an empty zip.
4. **A zone load does not grow with the zip** — met. EXECUTED: snapshot Paris 8,610,783 (≤ 15 M), Tokyo after it 1,305,014 (≤ 2 M); plain 8,610,337 and 8,632,570 on the two zips, 4 per member (≤ 1,000), Tokyo 1,429,349.
5. **Resources read as zipfile reads them** — met. EXECUTED: both binaries pass, and fail on main's set. My own 30 probes give the same answers on main's and 035's binaries, plain and snapshot, except `open("rb", pwd=None)` (Finding 3).
6. **Metadata answers from the zip's directory** — met. EXECUTED: snapshot miss 11,022,789 (≤ 20 M); plain 15,655,144 and 40,048,578, 4,620 per member (≤ 6,000); every distribution equal to upstream's objects, the kinds `["ZipDirectoryPath"]`. A prefixed zip on `sys.path` finds no root distribution, as on main.
7. **The pandas time-zone job** — met. EXECUTED: the golden matches on both binaries; snapshot 33,490,255 beyond its imports (≤ 60 M); plain 38,075,075. `test_goldens_reproduce_under_the_pinned_oracle` passes.
8. **A re-read after `invalidate_caches()`** — met. EXECUTED: 25,862 per member, `served` `"fast"`; fails on main's set.
9. **The rest of the judge, and the set** — met where it can be run here; the lane holds the rest. EXECUTED: lost 0; spec 033's and 051's checks pass. The zip is byte for byte main's (`daf2cdd8…`). `MANIFEST` differs from main's in exactly five `recipe` lines (two new, three changed). The growth account matches the four growths, but one supporting measurement does not hold on the final set (Finding 4). My full rebuild from pins in the worktree gave the same `SHA256SUMS` and `MANIFEST`, every byte (EXECUTED, below). Not run by me: a build in a clean clone, the release dry run and its rebuild jobs on other hosts (the landing notes leave these to the lane, as the criterion allows).

## The landing notes' numbers (EXECUTED, `build/review035/measure.log`, judge's driver)

| what | notes before → after | mine before → after |
|---|---|---|
| plain `-c pass` | 242.2 M → 151.0 M | 242,196,369 → 150,964,087 |
| plain `import pandas` | 4,991.6 M → 4,897.7 M | 4,991,551,151 → 4,897,681,596 |
| snapshot `-c pass` | 82.06 M → 81.90 M | 82,060,117 → 81,899,356 |
| snapshot `import pandas` | 82.08 M → 81.92 M | 82,082,564 → 81,922,408 |
| first zone, snapshot | 206.6 M → 8.61 M | 206,573,835 → 8,610,783 |
| metadata miss, snapshot | 221.9 M → 11.0 M | 221,967,070 → 11,022,789 |
| `version("numpy")`, snapshot | 360.9 M → 148.1 M | 360,991,107 → 148,059,233 |
| `import numpy.testing`, snapshot | 600.6 M → 387.7 M | 600,649,333 → 387,673,995 |
| importing `_zip_resources` | 1.31 M after resources, 1.24 M after metadata | 1,268,038 after resources, 1,316,888 after metadata |
| marshalled modules | 7,907 / 16,766 / 9,859 bytes | the same (`build/link/freeze.log`) |
| artifact bytes | +25,318 / +19,469 | the same (`ls -l`) |

All agree but the `_zip_resources` import, whose two figures read swapped and 0.04 M to 0.08 M off. My programs import the module and nothing more; the builder's may also have made `ZipDirectoryReader`. It changes nothing.

## Findings, most severe first

No finding is a defect in what the runtime's own zip gives. The code does what the specification says; I found no case where it gives an answer zipimport or `zipfile.Path` would not, apart from the two named in Findings 2 and 3.

### 1. Low-medium: four of the reader's fallback rules, and `zip_children`'s prefix rule, have no check; a regression in any of them would land green

Mutants applied to a copy of HEAD (`$R/mutate.py`), each run against `tests/unit/test_zip_directory.py` and the host fuzz against 3.15.0's own reader (EXECUTED):

| mutant | unit checks | fuzz differences (of 6,000) |
|---|---|---|
| drop `file_offset > cd_offset` → stock | 24 passed | **143** |
| drop `arc_offset < 0` → stock | 24 passed | **220** |
| drop the entry `0xFFFFFFFF` rule | 24 passed | 0 (but see below) |
| drop the `PK\x06\x06` probe, or the end-record maxima | 24 passed | 0 |
| drop the header-position checks | 24 passed | 0 (redundant with `arc_offset < 0`, INFERRED) |
| `zip_children` ignores `loader.prefix` | 24 passed | n/a |
| member reader drops `inflate.eof` | 24 passed | n/a |
| drop "walk ends at `cd_size`", cp437 as latin-1, no implied dirs, `head` for directories, `arc_offset` dropped | 1–4 failed each | 70–1,461 |
| member reader: no CRC, no encryption bit, no size limit, no local-name test; `open`'s order; `joinpath` without `resolve_dir`; children keyed wrongly; `==` without `NotImplemented`; `parent` without `/` | 1–3 failed each | n/a |

The guest checks would not catch the surviving ones either (INFERRED from reading criterion 3's zips: Zip64, cp437, explicit directories, prepended, truncated; none has a bad local offset, a negative archive offset, or a Zip64 extra without a Zip64 end record, and check 6 has no prefixed path).

Failure:
- **Bad offsets.** Without the `file_offset` test, a guest zip whose entry points past the directory is read fast, where zipimport raises `ZipImportError('bad local header offset')`. The dict then holds an offset the import reads garbage from. The fuzz found 143 such zips in 6,000.
- **A Zip64 extra without a Zip64 end record.** Streaming writers make these. The mutant gives `data_size == 4294967295` where zipimport reads 55 from the extra (EXECUTED, `$R/z64mut.py`; HEAD routes it to stock and agrees).
- **A prefixed zip.** Without the prefix test, `distributions(path=["/x.zip/sub"])` would list the archive's root distributions under `sub`. Upstream lists none (EXECUTED on HEAD: none, as on main).

Today's code is right on all of these (EXECUTED, the fuzz and the guest probes). This is about the judge after landing. **Fix:** add to `ODD` in `tests/unit/test_zip_directory.py` a zip with a local-header offset past the directory, one with the directory offset raised so `arc_offset < 0`, and a Zip64-extra entry with a plain end record. My `probe_guest.py` builds all three in a few lines each. Add a `zip_children` case for a zipimporter with a prefix. Optionally, add the host differential against `build/Python-3.15.0/Lib/zipimport.py` as a check when the tree is present.

### 2. Low: resources and metadata of a zip rewritten in place are as stale as zipimport's dict, and `version()` can raise `MetadataNotFound`; the README does not say so

EXECUTED (`build/review035/stale.log`), both binaries of each set. A guest writes `/w/s.zip` (package `spkg` with `r.txt`; `sdist-1.0.dist-info`), puts it on `sys.path`, imports `spkg`, reads `r.txt` and `version("sdist")`. Then it rewrites the zip in place, with `added.txt` and `sdist-2.0.dist-info`, and a new mtime, and does not call `invalidate_caches()`.

| after the rewrite | main | 035 |
|---|---|---|
| `files("spkg") / "added.txt"` read | `added` | `FileNotFoundError` |
| `iterdir()` of `spkg` | `__init__.py, added.txt, r.txt` | `__init__.py, r.txt` |
| `version("sdist")` | `2.0` | `MetadataNotFound` |
| `r.txt` read | new bytes | new bytes (the stale offset fails the checks; `zipfile` reads it) |

Upstream's `ZipReader` re-parses on every call, and `FastPath`'s lookup is keyed by the root's mtime, so stock sees the new zip. 035 answers from zipimport's dict until `invalidate_caches()`, after which it is fresh (EXECUTED, the probe's `fresh_added`). This is the design (Decision 7 says it for metadata: "as current as zipimport's view of it"), and imports from that zip are already as stale on main. But:
- Decision 6's accepted differences and the README's list do not name it, and the README says "the same bytes, listings … and errors".
- `MetadataNotFound` is a new error for a program that catches `PackageNotFoundError`: the stale folder name `sdist-1.0.dist-info/` is found, and its `METADATA` is gone.

The bytes stay safe: the member reader's local-header, size and CRC tests send a stale entry to `zipfile`. **Fix:** one line in the README's list of differences, and in Decision 6: "answers reflect zipimport's view of the zip, refreshed by `importlib.invalidate_caches()`, as imports do".

### 3. Low: `open(mode, pwd=None)` raises `ValueError` where `zipfile.Path.open` accepts it

EXECUTED (`build/review035/probe.log`, `open_pwd`): `files("tzdata").joinpath("zones").open("rb", pwd=None)` reads `Afric` on main and raises `ValueError: encoding args invalid for binary operation` on 035, both binaries. `zipfile.Path.open(self, mode='r', *args, pwd=None, **kwargs)` takes `pwd` as a keyword (READ, `Lib/zipfile/_path/__init__.py:337`). `ZipDirectoryPath.open` passes it into `**kwargs` (`recipes/zip_resources.py:168,187`). In text mode it would reach `TextIOWrapper` and raise `TypeError`.

`pwd` is not part of `Traversable`, so code written to the protocol is unaffected. But the README lists the `zipfile.Path` extras it lacks (`root`, `at`, `glob` and the rest) and says its errors are the same, and this one is neither listed nor the same. **Fix:** give `open` a keyword-only `pwd=None`, and hand any non-`None` `pwd` to the `zipfile` fallback; or add `pwd` to the README's list. A unit case either way.

### 4. Low: the growth account for `test_extra_preopens_work_on_the_snapshot` rests on a step-1 measurement that the final set does not repeat

The landing notes give "layout, not work" for the +902,876 (+0.1065%). The evidence they give is from step 1: "the same loop run a second time was 1.1 M cheaper on the new set than on the old". On the final set (EXECUTED, `build/review035/growth.log`, the probe's loop split out):

| snapshot | objects, types | setup | a plain loop (`type(o) is int`) | first `isinstance(o, io.IOBase)` loop | second |
|---|---|---|---|---|---|
| main | 62,302, 343 | 407,050,351 | 237,075,875 | 531,703,344 | 452,554,777 |
| 035 | 62,315, 343 | 406,794,370 | 237,059,796 | 532,542,965 | 452,939,511 |

The second loop is 0.38 M dearer, not 1.1 M cheaper. The conclusion still looks right (INFERRED): 13 more objects and the same 343 types; setup and the plain loop over the same objects did not grow; the growth is only in `isinstance`, whose ABC caches are sets keyed by type address. 13 objects at about 7,300 fuel each would explain about 0.1 M of the two loops' 1.22 M. The rest moves with the layout. **Fix:** restate the `--accept-growth` reason with final-set numbers (these, or the builder's own re-run), so the record does not cite a figure that no longer holds.

### 5. Informational

- **The specification's text still describes the pre-change design in two places.** Decision 6 says `ZipDirectoryPath` subclasses `Traversable` and `_zip_resources` imports `importlib.resources.abc`; Decision 8 and the Design table name `context/upstream/4-importlib-resources-zip-directory/`. The landing notes record both changes, and why (a metadata-only call would pay about 20 M to import `importlib.resources` and `tempfile`; folder `4-` was taken). A reader of Decision 6 alone gets the wrong class structure. The lane may want a one-line pointer in Decision 6 to the landing notes. `isinstance(path, Traversable)` holds in the guest (EXECUTED, the probe), because 3.15's `Traversable` is a `runtime_checkable` `Protocol` (READ).
- **The courtesy issue** says the differences found were "only for odd names". Findings 2 and 3 are two more. The owner may want them in the text before posting.
- **`ruff`.** `scripts/freeze_bootstrap.py:41` is 101 characters (E501). The rule covers only `src/` and `tests/`, which are clean. `ruff check recipes scripts` reports 23 findings on main and 23 on the branch, this line included (EXECUTED).
- **Intermediate commits** are clean on `ruff check` and `ruff format --check`. `pytest tests/unit` gives 916, 925 and 926 passed, with the same 1 failure and 3 errors. Those are the landing-lane and plugin tests, which need a git checkout and fail in any `git archive` export, as 051's review found. Each step is green as far as it can be judged without its own build.

## Correctness notes (no finding)

- **The reader against zipimport's semantics** (READ, then EXECUTED by the fuzz). It reads the same tail window. It finds the end record by `rfind` as zipimport does, and takes entries "on this disk" (offset 8), as zipimport does. Anything Zip64-shaped goes to stock. It applies the same three offset checks, and decodes names the same way (UTF-8 under the flag, ASCII, else stock). Its `head + name` equals the POSIX `_path_join` for names that are non-empty and do not end in `/`; other names call `_path_join`. It adds the implied directories with zipimport's own loop. zipimport reads entries until a non-`PK\x01\x02` signature and then compares the count. The fast reader requires the walk to end exactly at `cd_size`, where the end record's signature stands. Duplicated names keep dict semantics in both.
- **The two-phase start** (READ). `sys._stdlib_dir` is set before the import. A failure prints through the core phase's preliminary stderr and aborts. The recipe table is searched after the bootstrap table and before the frozen stdlib, and its two names clash with nothing. `_install_external_importers` and `init_zipimport` find phase 1's modules in `sys.modules`. Check 1 confirms the result on both binaries (EXECUTED).
- **Resources.** `ZipDirectoryReader` computes `ZipReader`'s prefix. `open_resource` (base class) raises `FileNotFoundError` for a missing name, as `ZipReader`'s does after it converts the `KeyError`. `name`, `suffix`, `stem`, `parent`, `str`, `joinpath`, `iterdir`, `is_*`, `exists` and `open`'s error order follow `zipfile.Path` line for line (READ). `as_file` on a file and on a folder, `contents`, `is_resource`, `read_text`, `available_timezones` and `pkgutil.get_data` all answer as on main (EXECUTED).
- **Metadata.** The wrapper sits on `PathFinder.find_distributions`, so it costs nothing per import. `zip_children` serves only a zipimporter with no prefix and returns upstream's own expression. A zip not on `sys.path` gets upstream's `zipfile.Path` (READ; EXECUTED, the unit check). Every distribution, version, entry-point group, `files()`, `packages_distributions`, `locate_file` and `origin` answers as on main (EXECUTED).

## Constitution checks

- **§4.1** — holds. No upstream file changes. The three run-time replacements are recipe files (`recipes/zip_directory.py`, `recipes/zip_resources.py`), hashed in `MANIFEST` (EXECUTED: the two new `recipe` lines match the files' SHA-256). The owner decided this is a recipe, not a patch (decisions 57–63). The pinned-tree check (`test_source_tree_matches_its_tarball`) passes.
- **§4.2** — holds. No new download. `downloads/SHA256SUMS` is untouched.
- **§4.3, §4.4** — hold. No host branch. `test_binary_is_a_core_wasm_module` and the import-wall checks pass: no new import (EXECUTED, the full run). The resource reader opens files through `_io.open_code`, a WASI read, as zipimport does.
- **§4.5** — holds. Nothing names an embedder. An embedder's open-code hook now also sees resource reads, which spec 035 chose (C3).
- **§4.6** — holds. Nothing large is in git. The artifacts are under ignored `build/`.
- **§4.9** — holds. The new checks assert fuel and equality, never time. The wall-clock figures are in the README's existing speed table and the landing notes, labelled as benchmark facts.
- **§4.10** — holds, with Finding 4's restatement and the `_zip_resources` figures noted above.
- **§4.11** — mostly holds. The README states the new `Traversable` and its differences. It misses Findings 2 and 3.
- **§4.13** — holds. `ruff` and `pytest` are green on `src/` and `tests/`.
- **§4.14** — holds. One local branch in a worktree outside the repository; nothing pushed.
- **§7** — nothing tripped. No edit in `build/` by hand, no new import, nothing fetched, nothing copied, no number reported that was not run. Everything the landing notes leave to the lane, they say so.

## The rebuild

EXECUTED (`build/review035/build.log`): `scripts/build.sh --plain`, every step from pins, exit 0. Step 60 gave `python.wasm` 31,786,310 bytes `c2e7c88f…`, step 70 the zip 11,203,143 bytes, and step 80 the snapshot 65,552,587 bytes `2993fb91…`. `diff` of `SHA256SUMS` and `cmp` of `MANIFEST` against the copies I saved before the build: identical. So the judged artifacts are HEAD's recipe files, and the set rebuilds the same on one host. `git status --short` is empty afterwards.

## Verdict (the build review, before the revision)

**Lands once F1 to F4 are fixed or answered in writing.** Every acceptance criterion that can be run here is met on the build's own artifacts, and they rebuild from pins to the same bytes. None of the findings changes an answer the runtime's own zip gives, and none needs a rebuild unless F3 is fixed in code. The work left is small: three unit zips and a prefix case (F1), one README line (F2), a keyword or a README line (F3), and a growth reason restated with final-set numbers (F4). If F3 is fixed in `recipes/zip_resources.py`, the binaries change, and the lane rebuilds and judges again. The lane still runs the clean-clone build, the release dry run and the rebuild on other hosts (criterion 9).

## One line

Install point A serves; a plain start falls from 242 M to 151 M fuel, a first time zone from 207 M to 8.6 M; the reader matches 3.15's own on 30,000 fuzzed zips and 156 in the guest; the rebuild repeats every byte. It lands once three unit cases, two README lines and a restated growth reason are in.

## Disposition (filled in by the author, then confirmed by the reviewer)

Copied from the implementer's record (`build/reviews-evidence/035-buildreview/disposition.md` in the main tree). A different agent from the original builder wrote it, on the same branch, in commits `5e30cfe`, `dce6cd3`, `31581f1`, `625a4d6` and `bb0905d` on top of `ca2ecc3`. The reviewed commits are unchanged.

1. **Finding 1 — fixed in `5e30cfe`.** Three zips join `ODD` in `test_odd_zips_go_to_the_stock_reader`: a local-header offset past the directory, a negative archive offset, and a Zip64 extra with a plain end record. `test_the_odd_zips_have_what_they_claim` asserts each zip's feature. `test_metadata_leaves_a_prefixed_zip_to_upstream` checks the prefix rule. A `stream not ended` case joins the member-reader check. `no_header_checks` still survives, because `arc_offset < 0` implies it. The host differential is not added, because the unit suite runs without a build tree.
2. **Finding 2 — fixed in `625a4d6`** (text). "Freshness" is now among Decision 6's accepted differences and in the README's list.
3. **Finding 3 — fixed in code in `dce6cd3`.** `open(mode="r", *args, pwd=None, **kwargs)`: with `pwd` `None` the read is fast; any other `pwd` goes to `zipfile.Path.open(..., pwd=pwd)`. The checks are a unit case, `test_a_password_goes_to_zipfile`, and check 5 on both binaries. The set was rebuilt from pins: `python.wasm` 31,786,374 `42344e2c…`, snapshot 65,548,702 `c4190ca0…`, the zip unchanged.
4. **Finding 4 — fixed in `bb0905d`.** The growth is restated on the final set: +1,150,255 (+0.136%) each, all of it in the `isinstance` loops. The step-1 claim is withdrawn.
5. **Finding 5 — fixed.** Decision 6, Decision 8 and the Design table now say what was built. The `_zip_resources` import row is marked. The courtesy draft names freshness and `pwd`. The E501 is fixed in `31581f1`. The unrun-locally check is named.

## Confirmation (2026-10-18)

By the same reviewer. I checked each disposition against the code and against runs of my own. I changed nothing in either tree. My logs are in the worktree's ignored `build/review035/` (`*-revised.log`, `pwd.log`, `growth2.log`), and the mutant copy is `$R/mut2/`, restored `cmp`-clean. I backed up `build/progress/latest.json` and put the builder's full-run copy back. Each claim below is EXECUTED unless labelled.

**The set under the judge is HEAD's.** `build/artifacts/` holds `python.wasm` 31,786,374 `42344e2c…`, the snapshot 65,548,702 `c4190ca0…`, the zip `daf2cdd8…` (unchanged) and `MANIFEST` `7c9ab793…`. All five `recipe` lines for the files 035 touches match HEAD's SHA-256. Against the build I reviewed, `MANIFEST` differs in exactly two lines: `recipes/zip_resources.py` and `scripts/freeze_bootstrap.py`. The builder's full judge (`build/revise035/judge-full.log`, 09:25) ran on this code: the only commit after it, `bb0905d`, touches only the specification. It reads `1221 passed, 10 skipped`, `271/274 pass · 0 gap · 3 blocked · 0 fail`, `lost 0 · unrun locally 1 · gained 20 · grew 4`. I found no reason to doubt it, so I did not run the full tier again.

**My runs.**
- The fast tier, `uv run pytest -m "not slow"`: `1213 passed, 10 skipped, 8 deselected`; `263/274 pass · 0 gap · 3 blocked · 0 fail · 8 deselected`; ratchet `lost 0 · gained 20 · grew 4`.
- The 035 check file, slow checks included, with the unit file: `54 passed`.
- `ruff check` and `ruff format --check` are clean on `src tests`. `ruff check` is clean on the three changed recipe and script files.
- My own metric comparison against `accepted.json` finds exactly four growths and 53 falls:
  - plain bytes +25,382 (+0.080%);
  - snapshot bytes +15,584 (+0.024%);
  - `test_extra_preopens_work_on_the_snapshot`, both orders, +1,150,255 (+0.136%).

  These match the disposition's list for the accept.

**F1 — confirmed.** I re-ran my 22 mutants on a `git archive` copy of HEAD. On HEAD the unit file gives `34 passed`.
- **Killed now:** `no_offset_check`, `no_arc_check`, `no_entry_max32` (2 failures each), `zr_zip_children_prefix` and `zr_no_eof` (1 each). These were the five survivors that mattered.
- **Still killed:** the 14 mutants the old checks caught.
- **Still surviving:** `no_header_checks` (implied by `arc_offset < 0`, as I inferred before), and `no_zip64_probe` and `no_end_max` taken one at a time. Each of these two is redundant with the other on every Zip64 zip the checks make, because `zipfile` maxes the end-record fields whenever it writes a Zip64 record (INFERRED). That is acceptable.

The three new hostile zips are built as I described them. `test_the_odd_zips_have_what_they_claim` guards each one's feature (READ).

**F3 — confirmed.** The code change is the smallest one that works (READ, `recipes/zip_resources.py:168-188`). `pwd is None` keeps the fast path, and any other `pwd`, `b""` included, goes to `zipfile` with the password. 3.15's `ZipFile.open` tests the password's type only inside its encrypted branch (READ, `Lib/zipfile/__init__.py:1812-1818`). So for a plain member the answer equals upstream's, whatever the `pwd`.

In the guest (`build/review035/pwd.log`), I read `files("tzdata")/"zones"` with `rb` and `r`, and `pwd` set to `None`, `b"k"`, `"k"` and `b""`. I also tried `open("w", pwd=b"k")`. All give the same answers on main's two binaries and on 035's two (`ValueError` for `w`). Before the fix, 035 raised `ValueError` for `pwd=None`.

Two new mutants in the copy are each killed by one unit case:
- the guard removed (`pwd` ignored on the fast path);
- `pwd` not passed on to `zipfile`.

The README and Decision 6 say that a `pwd` read goes to `zipfile`.

**F2 — confirmed.** The README paragraph and Decision 6's "Freshness" say what my stale-zip probe showed:
- the old listing until `invalidate_caches()`;
- `FileNotFoundError` for a new member;
- `MetadataNotFound`, not `PackageNotFoundError`;
- the bytes always current.

No code was meant to change, and none did.

**F4 — confirmed, and the account is now stronger.** My `growth.py` on the final snapshot (`build/review035/growth2.log`) reproduces every figure in the restated table:
- setup 406,969,480 (−80,871);
- the plain loop 237,034,514 (−41,361);
- the first `isinstance` loop 533,067,838 (+1,364,494);
- the second 453,338,054 (+783,277);
- 62,315 objects and 343 types.

One more fact backs the layout reading. `_zip_resources` is not loaded in the snapshot: `'_zip_resources' in sys.modules` is `False` at start. Even so, F3's change to that module's frozen bytes alone moved this check's growth from +902,876 to +1,150,255, and moved the snapshot by −3,885 bytes. The probe's work did not change; only the image's layout did. So "layout, not work" holds (INFERRED, now from two builds that differ only in an unloaded module's bytes). The growth is above Decision 10's 0.01% tolerance and is accepted with this reason. It is not a snapshot `-c pass` growth, and no plain check grew, so neither of Decision 10's red lines is crossed.

**F5 — confirmed.** Decision 6, Decision 8 and the Design table now describe the build. The courtesy draft names freshness and the `pwd` fix. `scripts/freeze_bootstrap.py:41` passes ruff (READ, plus the ruff run).

**Nothing new found.** The revision changes 15 lines of recipe code. The rest is checks and text. The checks fail on the mutants they were written for and pass on HEAD.

**Left to the lane, as before:**
- rebase onto main (spec 050 has moved it) and judge the exact commit in the main tree;
- accept with `--accept-judge` and `--accept-growth`, using the four growths and reasons above;
- the clean-clone build, the release dry run and its rebuilds on other hosts (criterion 9);
- copy this review into `context/reviews/`.

**Confirmed, it lands.**
