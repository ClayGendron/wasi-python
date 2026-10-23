# Review of 033 — The zip carries what packages need (the specification, before build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the constitution (§4.1, §4.9 to §4.12, §5.2, §5.6, §5.7), the specification, the research memo (`../research/2026-10-17-what-else-the-default-profile-carries.md`, findings 4a, 4c, 4e and 5, with `outputs/followup.tsv` and `outputs/guest/fuel.tsv`), decisions 43 to 48, and questions 57 and 58. In the code I read `scripts/make_stdlib_zip.py`, `scripts/steps/40_numpy.sh`, `50_pandas.sh`, `70_zip.sh`, `80_snapshot.sh`, `apply_patches.sh`, `scripts/assemble_artifacts.py`, `recipes/ctypes_stub.py`, `recipes/reactor_main.c` (`PREIMPORT`, `wizer_initialize`), the judge's zip and fuel rules (`tests/harness/artifacts.py`, `tests/harness/scoreboard.py`, `tests/harness/guest.py`, `tests/checks/test_v1_1_artifact_set.py`, `test_v1_3_data_stack.py`, `test_v1_5_rebuild_from_pins.py`, `test_rules.py`), spec 023's Decision 4, numpy's `_core/_internal.py`, `_core/_dtype_ctypes.py`, `ctypeslib/_ctypeslib.py`, `testing/_private/utils.py` and `_core/src/multiarray/descriptor.c`, pandas' `errors/__init__.py`, `io/clipboard/__init__.py`, `core/interchange/from_dataframe.py` and `plotting/_core.py`, and CPython 3.15's `Lib/ctypes/__init__.py`. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** `context/specifications/033-the-zip-carries-what-packages-need.md` as committed in `3b1c8f6`, against main at `c22694b`. The working tree holds other authors' uncommitted changes (`tests/harness/*`, spec 032). I did not read them for this review.
- **Ran (EXECUTED, darwin-arm64; `scripts/build.sh` not run; nothing in `src/`, `tests/`, `scripts/`, `recipes/` or the spec edited).** Scripts, prototypes and outputs are under `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/033-review/`:
  - `art/`: copies of `build/artifacts/` taken at 21:03. At 21:05 a `scripts/build.sh` that I did not start removed `build/artifacts/`. Every probe below ran on the copies.
  - `mkzip.py`: rewrites the zip with `make_stdlib_zip.py`'s own `pyc` and `member`, run as `PYTHONHASHSEED=0 uv run --no-project --python build/tools/python/bin/python3`. Variants: `same` (no change), `meta` (the five `METADATA` members only), `ctypes` (the stand-in only), `both` (the spec as written), `fix`, `lazy` and `dt` (findings 1 and 2).
  - `standin/`, `standin-fix/`, `standin-lazy/`, `standin-dt/`: my prototypes of Decision 5. They are review scaffolding, not proposed code.
  - `art-<variant>/python-snapshot.wasm`: made with the pinned `wasmtime wizer` and step 80's exact flags (`build/out/wizer-command.txt`), on a scratch root.
  - `hprobe.py`: runs a program through the judge's own driver (`tests/harness/guest.py`), which seeds clock and random alike, so fuel repeats. All counts are in `outputs.tsv`. Sizes are in `sizes.txt`.
  - `pkginfo/`: `PKG-INFO` extracted from the pinned `downloads/numpy-2.5.2.tar.gz` and `downloads/pandas-3.0.6.tar.gz`.

## What holds

- **The two problems are real.** EXECUTED (`outputs.tsv`, `meta same`, `pandas same`):
  - today `importlib.metadata.version("numpy")` raises `PackageNotFoundError`;
  - today `import pandas.io.clipboard` raises `ImportError: cannot import name 'c_size_t'`.

  So both guest checks can be seen failing first.
- **Decisions 1 and 2 give the right answers.** EXECUTED (`meta both`):
  - `version` gives `2.5.2` and `3.0.6`, equal to `__version__`;
  - `distributions()` is exactly numpy, pandas, python-dateutil, six and tzdata, each at its MANIFEST version;
  - `files("numpy")` is `None`;
  - `requires("pandas")` parses.
- **The member count and the plain-start cost are as stated.** EXECUTED:
  - the zip has 1,757 members (`sizes.txt`);
  - plain `-c pass` goes from 241,460,846 to 241,929,124 fuel, **+468,278** (78,046 per member). The spec says about 0.47 M.
- **The zip stays deterministic.** EXECUTED:
  - `mkzip.py same` reproduces today's zip byte for byte;
  - `both`, built twice, gives the same bytes twice;
  - a snapshot made from `same` equals today's snapshot byte for byte.

  The `METADATA` bytes are pinned. Member order and times come from `member()`, as today.
- **Reading `PKG-INFO` from the tree is consistent with spec 020.** The build tree's two `PKG-INFO` files equal a fresh extraction from the pinned tarballs (EXECUTED: `cmp`). The one carried patch (`recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`) does not touch `PKG-INFO` (READ). `test_source_tree_matches_its_tarball` judges the whole tree after the build, as it does every other input step 70 reads from a tree.
- **No startup import changes, and the snapshot freezes no lookup.** EXECUTED (snapshot and plain, `sys.modules` after `import numpy, pandas`): neither `importlib.metadata` nor `numpy.testing` is imported. READ: pandas' plotting loader imports `pandas.plotting._matplotlib` by name before it reads entry points (`plotting/_core.py:2177`). pandas' optional-dependency checks read `__version__`, not metadata.
- **Spec 018 (litter):** `--metadata` names one file, and wheels are read as zips. Nothing new is walked.
- **MANIFEST and SHA256SUMS:** the `recipe` lines are made from the tracked files under `recipes/` and `scripts/` (`assemble_artifacts.py:214`). So the stub's line goes and the two new lines come without new code, as Decision 10 says. The `package` lines already name all five distributions.
- **§4.12:** `LICENSES/` is untouched. Licence files inside `.dist-info` stay out. That is right.
- **The stdlib does not change behaviour.** READ: CPython's `platform`, `webbrowser` and `_ios_support` import `ctypes` only under Android, iOS or macOS branches. `multiprocessing.sharedctypes` would now import. Its first use reaches the `mmap` stand-in's `OSError` (INFERRED).
- **One builder can build it, and the ordering with spec 023 is right.** Both change step 70, so they never build at once.

## Acceptance criteria against evidence

1. **Six named checks, each seen failing first.**
   - The two guest checks: met. Both fail today (EXECUTED, above).
   - The unit check `test_a_tree_with_dist_info_stops_the_zip`, as designed: not met. It cannot reach Decision 3's line on the judge's host (finding 4).
2. **The zip's names and bytes.** The names and the plain-start cost are right on the prototype (EXECUTED). But this is a comparison for the build review, not a named check (finding 8).
3. **Same bytes from any host.** INFERRED holds: every new input is pinned bytes, and the same-host rebuild repeats (EXECUTED).
4. **The growth account.** Incomplete:
   - every plain check that imports numpy grows by about +7.2 M fuel, 15 times the `-c pass` figure;
   - every snapshot check grows by about +0.12 M fuel (both measured programs), above the 0.01% tolerance.

   Neither number is given, and no cap holds either (finding 2).
5. **Release dry run:** not judged before build.

## Findings, most severe first

1. **The stand-in's C types silently become `object` dtypes in numpy.** High. This is a silent wrong answer. It disguises the platform (§4.11), which Decision 5's "nothing more is claimed" means to avoid.
   - READ, why: numpy turns a type into a dtype in this order (`descriptor.c:94-136`):
     1. it asks for `__numpy_dtype__` or `dtype`;
     2. it asks whether the type's base comes from `_ctypes` (`_internal.py:946`);
     3. otherwise it treats the type as a plain Python class, which is `dtype('O')`.

     The stand-in's types pass the first two tests with no answer, so they get `dtype('O')`.
   - EXECUTED (`outputs.tsv`, `ctypes both`, on the stand-in as Decision 5 words it):
     - `np.dtype(ctypes.c_double)` is `dtype('O')`. Native numpy gives `float64`.
     - `np.asarray([1.5], dtype=ctypes.c_double)` returns an object array, with no error.
     - `import numpy.ctypeslib` now succeeds. Its scalar map collapses to one key, so `np.ctypeslib.as_ctypes_type(np.dtype("O"))` returns `c_bool`.
     - pandas' `from_dataframe(df.__dataframe__())` fails with the misleading `NotImplementedError: Converting dtype('int64') to a ctypes type`.

     Today each of these raises `AttributeError`.
   - So the Scope line "`numpy.ctypeslib` and `ndarray.ctypes` … fail before this change and after it" is wrong:
     - `numpy.ctypeslib` imports after the change;
     - `ndarray.ctypes` changes from `AttributeError` to the stand-in's `OSError`.
   - A plain refusal is not the fix. EXECUTED (`fix` variant): a `__numpy_dtype__` that raises `OSError` makes every numpy path raise. But `import numpy.ctypeslib` then raises `OSError`, which `hasattr(np, "ctypeslib")` and `inspect.getmembers(np)` do not catch. Both then fail (`has fix`). Today the same calls return `False` and 531 members.
   - Fix (EXECUTED, `dt` variant):
     - Give the simple types a `__numpy_dtype__` descriptor. It returns `sys.modules["numpy"].dtype(cls._type_)`. This is what numpy itself does for a real ctypes simple type (`_dtype_ctypes._from_ctypes_scalar`). It is a fact about the type, not a foreign call.
     - `Structure`, `Union`, `POINTER(…)` and `CFUNCTYPE(…)` types raise the `OSError`, since the stand-in computes no layouts.
     - Result: `c_double` → `float64`, `c_long` → `int32`, `c_longdouble` → `float128`, `c_void_p` → `uint32`. `hasattr(np, "ctypeslib")` is `True`, and `getmembers` works.
     - Also give each simple type `__ctype_le__` (itself) and `__ctype_be__`, as CPython does. `as_ctypes_type` reads them (`_ctypeslib.py:394`); without them it raises `AttributeError` (`dt dt`).
   - Add these to `test_ctypes_stand_in_names_what_packages_import`, each seen failing first (today: `AttributeError`):
     - `np.dtype(ctypes.c_double) == np.float64` and `np.dtype(ctypes.c_long) == np.int32`;
     - `hasattr(np, "ctypeslib")` returns without raising;
     - `np.arange(3).ctypes` raises the `OSError`;
     - pandas' `from_dataframe(df.__dataframe__())` raises the `OSError` (from `ctypes.cast`).

     Then correct the Scope line.
2. **The growth account leaves out numpy's import and the snapshot's moves, and caps neither.** Medium. The account is the reason a judge-visible growth gets accepted. It must name what will grow.
   - READ: numpy imports `ctypes` first (`numpy/_core/_internal.py:20`), before pandas does. So Decision 7's "because pandas imports it" and criterion 4's "plain checks that import pandas" undercount: every numpy job pays too.
   - EXECUTED (`outputs.tsv`), the stand-in made eagerly in one loop, as Design asks:
     - plain `import numpy`: +7,812,307 fuel (+0.69%);
     - plain `import pandas`: +7,795,433;
     - of each, about +7.2 M is the stand-in. The members alone give +0.31 M on numpy (`np meta`);
     - snapshot `-c pass`: +124,432 (+0.15%);
     - snapshot pandas groupby: +116,732.
   - EXECUTED, bytes (`sizes.txt`): the zip grows +17,056 (inside the 10 to 25 KB band). The snapshot grows +13,956.
   - Fix, in two parts.
     - **Build the types on first use.** Use a module `__getattr__` (PEP 562) that makes the type table the first time a type name is asked for. numpy and `pandas.errors` only `import ctypes`, so they never pay for it. EXECUTED (`lazy` variant): plain `import numpy` grows +1,971,918 and plain `import pandas` +1,820,670, each including the members. Snapshot `-c pass` grows +145,059, about the same as eager. So the snapshot's move is not the type objects. I did not find its cause: the metadata alone moves it +87,744 (`pass meta+snap`). Also keep the `__numpy_dtype__` fix of finding 1 inside the lazily made types.
     - **Write the measured account into criterion 4, with caps.** For example:
       - plain `-c pass` ≤ +0.6 M (as now);
       - plain `import numpy` ≤ +2.5 M with the lazy stand-in;
       - snapshot `-c pass` ≤ +0.2 M;
       - zip ≤ +25 KB; snapshot ≤ +20 KB.

       Above a cap is a finding for the build review. Then the `--accept-growth` reason can cite numbers, not "small moves".
3. **`import numpy.testing` costs a third more on the snapshot, and the lookup cost is larger than stated.** Medium-low.
   - EXECUTED (`nt`): on the snapshot, `import numpy.testing` goes from 464,071,491 to 600,137,174 fuel, **+136 M (+29%)**. numpy now finds its distribution and parses its `METADATA` (`testing/_private/utils.py:61`). It gains nothing: `IS_INSTALLED` stays `False` because `locate_file` returns a `zipfile.Path`, not `NUMPY_ROOT` (`utils.py:87`). `np.testing.assert_allclose` is common in generated code. So "programs that never ask for metadata pay nothing" is not quite true.
   - EXECUTED (`v1`, `eps`, `imd`): on the snapshot, `import importlib.metadata` costs 35.4 M over `pass`. Then the first `version("numpy")` costs about 361 M more:
     - about 219 M scans the zip's directory, and today's zip pays that already (`v1 same`, 336.2 M total);
     - about 142 M is new: reading and parsing the found `METADATA`.

     Decision 7's "about 0.2 G for the first lookup" counts the scan only. A second lookup costs 23 M more (`v2`).
   - Fix: in Decision 7, the growth account and the README, state:
     - `numpy.testing`'s +136 M on the snapshot;
     - that the first lookup costs about 0.36 G on the snapshot, of which about 0.14 G is new.

     Say that "the zip's directory is read once" (question 60 replaces `importlib.metadata`'s zip search) is where it gets cut. Keeping numpy's `METADATA` is still right: tier A needs the rule for every distribution.
4. **`test_a_tree_with_dist_info_stops_the_zip` cannot reach Decision 3's line on the judge's host.** Medium-low. The check would fail first for the wrong reason, then could never pass honestly.
   - READ: `make_stdlib_zip.main` stops first unless the interpreter is the line's 3.15 (`line.target()`, `line.conf`: `PYTHON_VERSION=3.15.0`). It then needs `PYTHONHASHSEED=0` and `--lib`, and at the end it needs `_sysconfigdata` and `numpy/__config__.py` among the members. EXECUTED: the judge's Python is `uv run python -V` → 3.14.2.
   - So `main` stops with "compile with Python 3.15, not 3.14.2" before any tree is walked. A test that accepts any `SystemExit` would pass for that reason.
   - Fix: do Decision 3's test in a function the unit check calls directly, as `test_the_zip_walk_skips_litter` calls `walk`. For example, `walk` raises at the top level, or a small `tree_members(tree)` does. Assert the exact one line.
5. **The stand-in's types are not CPython's types on wasm32.** Low. It is cheap to be exact.
   - READ (`Lib/ctypes/__init__.py`): where `int` and `long` are the same size, CPython makes these aliases, not separate classes:
     - `c_int` is `c_long` and `c_uint` is `c_ulong` (180-193);
     - `c_size_t` is `c_uint` and `c_ssize_t` is `c_int` (573-581);
     - `c_int8` is `c_byte` and `c_uint8` is `c_ubyte`;
     - each of the other fixed-width types is the last of `c_short`, `c_int`, `c_long`, `c_longlong` (or the unsigned four) of its size (652-669). So `c_int32` is `c_long`.

     The spec makes each a class of its own. Then `POINTER(c_int) is POINTER(c_long)` and `c_int32 is c_long` are `False`, where wasm32's real ctypes says `True`.
   - Fix: make the aliases by CPython's rule, from `struct.calcsize` in the guest. That gives fewer classes and a cheaper import (finding 2). The guest check asserts two of the identities.
6. **The rule's edges are not all `OSError`, and one of them can break an import.** Low.
   - EXECUTED on my prototype of the stand-in as worded (`edges both` in `outputs.tsv`); the built stand-in will do the same unless it adds these names:
     - `c_char * 4` raises `TypeError`, not `OSError`;
     - `from_buffer`, `from_address`, `in_dll` and `from_param` raise `AttributeError`;
     - `@CFUNCTYPE(c_int, c_int)` on a module-level `def` makes an instance, so it raises `OSError` at import time. Importers that guard with `except ImportError` will not catch it.
   - Fix: say each in Decision 5. Or give the types a metaclass whose `__mul__` and `__rmul__` raise the `OSError`, so array types refuse like the rest. Add `c_char * 4` to the unit check.
7. **Decision 3 guards `.dist-info` but not `.egg-info`.** Low. It matters for spec 023.
   - READ: `walk` skips `.dist-info` folders and nothing else of the kind. A tree holding `<name>.egg-info/` packs it today. `importlib.metadata` reads egg-info, so that would be a second, unpinned-by-rule route to metadata, with `SOURCES.txt` beside it.
   - INFERRED: Pillow's and kiwisolver's sdists, which spec 023 builds from source, are setuptools sdists and usually carry `<name>.egg-info/` under their package root. They are not pinned yet, so I could not check.
   - Fix: `walk` skips `.egg-info` too, and Decision 3's stop covers a top-level one. Add a case to the unit check.
8. **Criteria 2 and 3 are comparisons for the build review; name how they are done.** Low.
   - Criterion 2 compares member names and bytes with today's zip. Write the command:
     - `unzip -Z1` on both zips, diffed;
     - a byte comparison of every shared member;
     - a `cmp` of each `METADATA` against its source.

     Record the result in the landing notes.
   - This review's `mkzip.py same` shows one way: it rebuilds today's zip byte for byte from `make_stdlib_zip.py`'s own functions.

## Constitution checks

- §4.1 patches: none. The stand-in is a recipe file, and `PKG-INFO` is read unchanged. INFERRED, for the record: numpy's `METADATA` says `Version: 2.5.2` while its tree carries one recorded patch. That equals `numpy.__version__`, and the patch is in `MANIFEST` and the CHANGELOG. I see no change needed.
- §4.2 pins: no new input. Both `PKG-INFO` files come from pinned tarballs.
- §4.4 two imports: unchanged. The stand-in loads nothing and calls nothing.
- §4.6 artifact set: the zip and the snapshot change. `python.wasm` does not (step 60 is untouched).
- §4.9 tests count: the guest checks assert equality and exceptions. The growth is fuel and bytes. No clock is read.
- §4.10 evidence: the spec's 0.47 M is now EXECUTED. Its "about 0.2 G" lookup and its "small moves" are corrected or quantified above (findings 2 and 3).
- §4.11 platform semantics: finding 1. As worded, the stand-in disguises the platform inside numpy. Question 58's banner is fine: `test_version_states_the_platform_semantics` needs only the word `ctypes`, and the README will say what the stand-in does.
- §4.12 licences: unchanged and right.
- §4.13 tooling: no new dependency.
- §4.15 safe by default: no default loosens.
- §5.2 no open questions: none. Questions 57 and 58 are decided in the spec.
- §5.7 one build-class change at a time: stated for spec 023. The same holds for "the zip's directory is read once", which replaces `importlib.metadata`'s zip search (question 60) and will move finding 3's numbers.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed.**
   - In "The problem": a paragraph on the trap, numpy's three steps and the review's `dtype('O')`.
   - In Decision 5, "numpy's dtypes":
     - each simple type has a class-level `__numpy_dtype__` returning `sys.modules["numpy"].dtype(cls._type_)`, as `_from_ctypes_scalar` does;
     - each numeric type has `__ctype_le__` (itself) and `__ctype_be__` (itself for one-byte types, else a big-endian twin read as numpy reads a real one);
     - every non-simple type's `__numpy_dtype__` raises the `OSError`;
     - the rejected all-raising variant is recorded, with why.
   - The guest check (Decision 8) adds:
     - `np.dtype(c_double) == float64` and `np.dtype(c_long) == int32`;
     - the big-endian twin's dtype;
     - `as_ctypes_type(np.int32) is c_long`;
     - `hasattr(np, "ctypeslib")`;
     - `np.arange(3).ctypes`, `from_dataframe(df.__dataframe__())` and `np.dtype(Structure)` raising the `OSError`.

     Each is seen failing first against today's stub and against a mutant without `__numpy_dtype__` (criterion 1).
   - The Scope's `numpy.ctypeslib` line is corrected: it imports now, `as_ctypes_type` works, and the instance and memory paths raise `OSError`.
2. **Fixed.**
   - Decision 5 builds the types on first use (PEP 562 `__getattr__`, `__dir__`, `__all__`). Only the constants and `WinError` are made at import.
   - Decision 7 now carries the review's measured table:
     - plain `-c pass` +468,804; plain `import numpy` +1,971,918; plain `import pandas` +1,820,670;
     - snapshot `-c pass` +145,059; snapshot groupby +135,928;
     - zip +17,458 bytes; snapshot +13,536 bytes;
     - the eager cost avoided (+7.8 M).
   - Decision 7 corrects "because pandas imports it": numpy imports `ctypes` first.
   - Criterion 4 now has the review's figure and a cap for each metric:
     - plain without numpy ≤ +0.6 M; plain with numpy or pandas ≤ +2.5 M;
     - snapshot ≤ +0.2 M;
     - zip ≤ +25 KB; snapshot ≤ +20 KB; `python.wasm` 0.

     The snapshot's growth is accounted honestly: the measured split between metadata and stand-in, the cause stated as not profiled, and the INFERRED one named.
3. **Fixed, and answered.**
   - Decision 7 states the snapshot costs:
     - `import importlib.metadata` about 35 M;
     - the first `version("numpy")` about 361 M more: about 219 M of scan that today's zip already pays, and about 142 M new;
     - a second lookup about 23 M;
     - `import numpy.testing` +136 M, with why it gains nothing;
     - no existing check imports it.
   - The README states the lookup and `numpy.testing` costs until 035 lands. Criterion 4's account restates them.
   - **Whether 035 recovers it.** 035's part 3 recovers the ~219 M scan: its own table puts a snapshot miss at about 10 M. Whether it recovers the ~142 M of reading and parsing `METADATA`, or `numpy.testing`'s +136 M, is not known. 035 does not replace the parse. 035's builder measures both with 033 in and records what remains. Keeping numpy's `METADATA` stays, for the reason the review gives.
4. **Fixed.**
   - Decision 3's stop is in `tree_members(tree)`, which `main` calls for each `--tree`.
   - The unit check (renamed `test_a_tree_with_package_metadata_stops_the_zip`) calls it directly, as the litter check calls `walk`, and asserts the exact line.
   - Design says why: `main` needs the line's 3.15, and the judge's Python is 3.14.
5. **Fixed.** Decision 5 makes the aliases by CPython's rule, from `struct.calcsize` in the guest:
   - `c_int`/`c_uint` → `c_long`/`c_ulong`;
   - `c_longlong` and `c_longdouble` collapse only when sizes match;
   - `c_size_t`/`c_ssize_t` by pointer size;
   - `c_int8`/`c_uint8` → `c_byte`/`c_ubyte`;
   - the other fixed widths are the last same-size type;
   - `c_time_t` is `c_int64`.

   It lists what this gives on wasm32. The guest check asserts `c_int is c_long` and `c_int32 is c_long`, and checks `c_time_t` against `SIZEOF_TIME_T`. The unit check asserts `c_int8 is c_byte`.
6. **Fixed, mostly by giving the edges types rather than refusals.**
   - Array types: `t * n` and `n * t` make a stand-in array type, so a `_fields_` with `c_char * 16` still declares at import. `sizeof` of one is its length × the element's size. Instantiating one, or asking numpy for its dtype, raises the `OSError`.
   - `from_buffer`, `from_buffer_copy`, `from_address`, `from_param` and `in_dll` raise the `OSError`.
   - `sizeof` of a non-stand-in raises `TypeError`, as CPython does.
   - The `@CFUNCTYPE` decorator, and any module-level instance, raise `OSError` at import, not `ImportError`. "The edges, stated" in Decision 5 says so and why it is accepted.
   - The unit and guest checks cover `c_char * 4`, the classmethods and the refusals.
7. **Fixed.**
   - `walk` skips `.egg-info` folders.
   - `tree_members` stops on a top-level `.dist-info` or `.egg-info`.
   - `wheel_members` drops a top-level `.egg-info`.
   - Today's inputs hold none, so no member is lost (EXECUTED by the author: `find` over the two trees and the two sdists, and `unzip -Z1` of today's zip, count 0).
   - Unit cases: a top-level `.egg-info` stops; a nested one is skipped; a wheel's is dropped.
   - Decision 9 notes the consequence for spec 023's Pillow and kiwisolver.
8. **Fixed.** Criterion 2 names the commands, each with its expected output, to be recorded in the landing notes:
   - the sorted `unzip -Z1` diff, with its exact expected lines;
   - a `uv run --no-project python -I` byte comparison of the shared members, expecting `1750 shared; 0 differ`;
   - five `cmp`s of `METADATA` against `PKG-INFO` and the wheels' `METADATA`;
   - a `cmp` of `python.wasm`.

   Criterion 3 names:
   - the dry run (`gh workflow run release.yml --ref <branch>`), with its `rebuild` and `same-bytes` jobs, its run number to the landing notes;
   - the litter re-run's `cmp` of `SHA256SUMS`.

## Verdict

Build after a revision. The metadata half is right as written: it gives true answers, the zip stays the same bytes from every host, and plain start grows by the stated 0.47 M. The `ctypes` half needs one real change. As worded, its types reach numpy as plain classes, so `np.dtype(ctypes.c_double)` becomes `object` with no error (finding 1). The fix is small and was run: hand numpy the same dtype it would compute for a real ctypes type, and refuse the rest. Make the stand-in lazy, and write the measured growth, with caps, into criterion 4 (finding 2). Fix the one unit check that cannot run on the judge's host (finding 4). Findings 3 and 5 to 8 are statements and small cases.

One line: keep the metadata as designed, but the `ctypes` stand-in must not turn C types into `object` dtypes in numpy, so give numpy the true dtype, build the types lazily, and account for the growth with numbers and caps.

## Confirmation (2026-10-17)

- **Reviewer:** the same fresh agent that wrote the review above (Claude Opus 5.5), not the author. I read the revised specification (uncommitted, 648 lines), the Disposition above, and questions 57 and 58. I edited nothing but this section.
- **Re-ran (EXECUTED, same machine, on the copies taken at 21:03; `build/artifacts/` not touched; `scripts/build.sh` not run).** New files are in the same scratch folder (`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/033-review/`):
  - `standin-full/`: a prototype of the revised Decision 5 as written. It is one module with lazy PEP 562 types, CPython's aliases, `__numpy_dtype__`, the big-endian twins, array types, refusing classmethods, and `sizeof` raising `TypeError` for a non-stand-in.
  - `standin-split/`: the same code, with the builder moved into a submodule, `ctypes/_types.py`. `__init__` imports it only on the first type lookup. That makes one more member (1,758).
  - `p_check.txt`: every assertion of Decision 8's `test_ctypes_stand_in_names_what_packages_import`, written out.
  - `jobs.py`: runs the five golden jobs exactly as `_run_job` does.
  - `outputs-confirm.tsv` and `sizes-confirm.txt`: the results. Snapshots were made with step 80's flags, as before.

### Each finding

1. **Confirmed. The dtype fix works.** EXECUTED (`check full`, `check split`, on both binaries): `p_check.txt` prints `OK`. It covers:
   - `np.dtype(c_double) == float64` and `np.dtype(c_long) == int32`;
   - `np.dtype(c_int32.__ctype_be__) == >i4`;
   - `as_ctypes_type(np.int32) is c_long`;
   - `hasattr(np, "ctypeslib")`, and `inspect.getmembers(np)`;
   - each refusal raising the `OSError` with the message: `arr.ctypes`, `from_dataframe`, `CDLL(None)`, `c_int(1)`, the `Structure` instance, `byref`, `from_buffer`, `np.dtype(Structure)` and `WinError`;
   - every `SIZEOF_…` comparison, including `c_time_t` against `SIZEOF_TIME_T`;
   - `c_int is c_long` and `c_int32 is c_long`;
   - `sizeof(c_char * 16) == 16`;
   - `import ctypes.wintypes` raising `ImportError`.

   Against today's set the same program fails at `import pandas.io.clipboard` (`check same`). So the check can be seen failing first. The Scope's `numpy.ctypeslib` text is now right.
2. **Not yet met. The stand-in as now written breaks two of criterion 4's caps on my prototype.** One statement in Decision 7 is refuted.
   - Decision 7 says the dtypes, twins and arrays "add bytecode but no fuel at import (INFERRED)". That is not so. EXECUTED (`standin-full`, against today):

     | metric | growth | cap |
     |---|---|---|
     | plain `-c pass` | +467,348 | ≤ +0.6 M ✓ |
     | plain `import numpy` | +2,889,359 | ≤ +2.5 M ✗ |
     | plain `import pandas` | +3,024,143 | ≤ +2.5 M ✗ |
     | snapshot `-c pass` | +230,914 | ≤ +0.2 M ✗ |
     | snapshot groupby | +220,878 | ≤ +0.2 M ✗ |
     | snapshot CSV-and-groupby program | +308,325 | ≤ +0.2 M ✗ |
     | the zip | +20,004 bytes | ≤ +25 KB ✓ |
     | the snapshot | +571 bytes | ≤ +20 KB ✓ |

     A larger `ctypes/__init__` costs fuel to load on every plain numpy import. It also costs fuel on every snapshot call, because the snapshot holds it. The types are never built in either case.
   - Moving the builder out of `__init__` fixes it. EXECUTED (`standin-split`):

     | metric | growth |
     |---|---|
     | plain `-c pass` | +542,066 (7 members) |
     | plain `import numpy` | +983,668 |
     | plain `import pandas` | +835,650 |
     | snapshot `-c pass` | +154,670 |
     | snapshot groupby | +142,254 |
     | snapshot CSV-and-groupby program | +16,277 |
     | the zip | +20,532 bytes |
     | the snapshot | +7,285 bytes |

     INFERRED: putting the builder in `ctypes/util.py` instead, as a private function, gives the same import cost with no seventh member. `ctypes.util` is small apart from it, and `import ctypes.util` would load the builder's code without running it.
   - **A fixed cap per heavy check is fragile.** EXECUTED (`jobs.py`), the golden jobs' growth for full and then split:
     - `numpy_csv`: +1,804,316 and +1,146,557;
     - `pandas_csv`: +4,176,863 and +2,765,223;
     - `numpy_random`: +8,862,867 and +231,520;
     - `compress`: +536,397 and +764,393. It does not import numpy, so the 0.6 M cap applies, and split breaks it;
     - `sqlite`: +3,789,717 and +701,298.

     In none of these runs were the types built (EXECUTED: a copy of `numpy_random` that prints `'c_long' in vars(ctypes)` at its end prints `False` on both). That two-line tail alone shrank the gap between full and split on `numpy_random` from 8.6 M to 1.8 M. INFERRED: on a 4 to 6 G-fuel program, the collector's timing moves fuel by a few M whenever the heap's contents change. So an absolute +2.5 M cap on the golden jobs will trip on noise, not on a regression.
3. **Confirmed.** Decision 7 carries the lookup costs, and the README and criterion 4 restate them. The answer on what spec 035 recovers is honest: the ~219 M scan yes, the ~142 M parse and `numpy.testing`'s +136 M not known, and 035's builder measures them.
4. **Confirmed.** `tree_members(tree)` is called directly, and Design says why. Note for the builder: if the stand-in's builder moves to a submodule (condition 1), the host unit check must load the recipe folder as a package under its private name, so that the relative import resolves.
5. **Confirmed.** The aliases follow CPython's rule (`Lib/ctypes/__init__.py`, as cited). The guest check asserts two identities and `c_time_t`. My prototype of the rule gives every identity Decision 5 lists for wasm32.
6. **Confirmed.** Array types, refusing classmethods, `sizeof`'s `TypeError` and the stated import-time edge all behave as written on the prototype.
7. **Confirmed.** The `.egg-info` skip and stop, the unit cases, and the note for spec 023.
8. **Confirmed.** Criterion 2's commands are exact. `1750 shared` is right: 1,751 minus `ctypes.pyc`. Criterion 3 names the dry run and the litter re-run. If condition 1 adds a member, the expected diff and the 1,757 change with it.

### Conditions for build

Write both into the specification before the builder starts. Neither needs another review if it is written as stated here. The lane checks it against this section.

1. **Keep `ctypes/__init__` small.** Decision 5 puts the type builder outside the module that numpy and pandas import:
   - either in `ctypes/util.py` as a private function (INFERRED: no new member);
   - or in a new `ctypes/_types.py` member (EXECUTED above: +1 member).

   Decision 7 drops the refuted INFERRED sentence and carries the measured `standin-split` row instead. If the builder chooses the new member, Decision 7, criterion 2's expected diff and the member count say 1,758.
2. **Re-base criterion 4's caps on what is deterministic.**
   - Keep absolute caps for the small programs, where fuel is stable:
     - plain `-c pass` ≤ +0.6 M;
     - plain `import numpy` and `import pandas` ≤ +1.5 M;
     - snapshot checks ≤ +0.2 M;
     - the zip ≤ +25 KB, the snapshot ≤ +20 KB, `python.wasm` 0.
   - For the heavy plain checks (the golden jobs and every other plain check above 1 G fuel, `compress` included), cap each at ≤ +0.2% of its accepted value. The largest growth measured here, with the types never built, was +0.18% (`numpy_random`, one-module stand-in); with condition 1 it was at most +0.05% (`pandas_csv`).
   - For any heavy check above +2.5 M, require evidence. The account shows, for that check, that the stand-in's types were not built (or why they were), and attributes the rest to the collector's timing, as measured here.
   - Any other plain check that does not import numpy stays at ≤ +0.6 M.

   This keeps a real regression visible without making noise a finding.

### Verdict

**Confirmed for build once conditions 1 and 2 are written into the specification.** Every finding's disposition is right in substance:
- the dtype fix passes every assertion Decision 8 names, and fails today;
- the metadata half stands as reviewed.

What remains is cost: where the builder's code lives, and how the caps treat noise. Both are now measured.

One line: the revised stand-in tells numpy the truth and passes its check, but its builder must live outside `ctypes/__init__`, and the heavy checks need a relative cap, or criterion 4 fails on cost and on noise rather than on regressions.

### Author's note: where each condition went (2026-10-17)

1. **Condition 1: written in, with the measured option.** The type builder goes in a new `ctypes/_types.py`. `__init__`'s `__getattr__` imports it on the first type lookup. I did not choose the `util.py` option: it is unmeasured.
   - Decision 5's "Where it lives" and "Built on first use" now name three files and say why: eager +7.2 M; builder kept in `__init__` +2.9 M on `import numpy` and +0.23 M per snapshot call.
   - Decision 7:
     - the members are now **1,758, +7**;
     - the refuted INFERRED sentence is gone;
     - the table is now the `standin-split` row: plain `-c pass` +542,066, `import numpy` +983,668, `import pandas` +835,650, snapshot `-c pass` +154,670, groupby +142,254, CSV-and-groupby +16,277, zip +20,532 bytes, snapshot +7,285 bytes;
     - it adds the golden jobs' growth with split and the types-not-built evidence.
   - Decision 10: seven members, three recipe lines.
   - Design: three recipe rows, three `--file` lines. The unit check now loads the recipe folder as a package under its private name, as your finding 4 note asks, and checks that `_types` is not loaded before the first lookup.
   - Criterion 2's expected diff adds `> ctypes/_types.pyc`, and the count is 1,758. `1750 shared` is unchanged.
2. **Condition 2: written in, as stated.** Criterion 4's caps:
   - plain `-c pass` ≤ +0.6 M;
   - plain `import numpy`, `import pandas`, and import-only checks ≤ +1.5 M;
   - every other plain check above 1 G fuel (the golden jobs, `compress` included) ≤ +0.2% of its accepted value;
   - any other plain check ≤ +0.6 M;
   - snapshot checks ≤ +0.2 M;
   - zip ≤ +25 KB, snapshot ≤ +20 KB, `python.wasm` 0.

   A heavy check above +2.5 M needs, for that check, the `'c_long' in vars(ctypes)` evidence that the types were not built (or why they were), with the rest attributed to the collector's timing.

Also: the spec's Status line says "confirmed for build with conditions, written in", and question 57's figures now use the `standin-split` numbers.
