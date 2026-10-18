# 033 — The zip carries what packages need

- **Status:** drafted 2026-10-17. Revised the same day against its pre-build review
  (`../reviews/033-the-zip-carries-what-packages-need-spec-2026-10-17.md`): all eight findings are
  fixed here, and its Disposition says where. **Confirmed for build with conditions, written
  in:** the review's Confirmation set two conditions. Condition 1 (the type builder outside
  `ctypes/__init__`) is in Decisions 5, 7 and 10, Design and criterion 2. Condition 2 (the caps
  re-based) is in criterion 4. It changes the build recipe and the artifact set (constitution
  §5.6), and it is build-class (it touches `scripts/` and `recipes/`; §5.7). Built 2026-10-17 on
  `spec/033-the-zip-carries-what-packages-need`, awaiting its build review: two of criterion 4's
  caps are exceeded (by 24,482 and 15,125 fuel, both shown to be the collector's timing), and the
  release dry run is the lane's (Landing notes).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/make_stdlib_zip.py`, `scripts/steps/70_zip.sh`), recipe
  files (`recipes/ctypes_stand_in/__init__.py`, `_types.py` and `util.py` replace
  `recipes/ctypes_stub.py`),
  judge additions (`tests/checks/test_v1_3_data_stack.py`, `tests/unit/test_build_scripts.py`),
  `README.md`, `CHANGELOG.md`.
- **Depends on:** 003 (step 70 and the zip's rules), 012 (the same bytes from any host), 018
  (no litter in the zip), 020 (each source tree equals its pinned tarball plus the recorded
  patches), 004 and 009 (the licence notices in `LICENSES/`). All landed.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`,
  item 1 of "The order of specifications":
  - finding 4a: step 70 drops `.dist-info`, so packages that read their own metadata fail
    (`df.to_markdown()` through tabulate, plotly, markdown's entry points). Keeping `METADATA`
    and `entry_points.txt` fixed tabulate and markdown (EXECUTED);
  - finding 4c: the `ctypes` stand-in is too thin for sympy and threadpoolctl (EXECUTED);
  - finding 5: 77,912 fuel per zip member on every plain start (EXECUTED).

  The evidence is beside the memo: `outputs/followup.tsv`,
  `outputs/guest/probe-sympy.stderr.txt`, `outputs/guest/probe-threadpoolctl.stderr.txt`. The
  owner's decisions 43 to 48 (`../decisions.md`) and the roadmap's milestone 4
  (`../roadmap.md`). The pre-build review's prototypes and measurements (EXECUTED there, on
  copies of the main tree's artifact set; its `outputs.tsv` and `sizes.txt`) give the cost
  figures in Decision 7 and criterion 4.

## The problem

Two things in today's zip stop pure-Python packages that would otherwise run.

**The zip has no package metadata.** Step 70 packs a wheel's code and drops its whole
`.dist-info` folder (`make_stdlib_zip.py`, `wheel_members`). numpy and pandas come in as trees
with no `.dist-info` at all: numpy from `meson install`, pandas from the sdist's folder. So in
the guest `importlib.metadata.version("numpy")` raises `PackageNotFoundError` (EXECUTED by the
review). Packages that ask for their own version or their entry points break:
- tabulate reports version `unknown`, and pandas then refuses it, so `df.to_markdown()` fails
  with `InvalidVersion: 'unknown'`;
- markdown's extensions by short name fail.

numpy itself asks at `import numpy.testing` (`numpy/testing/_private/utils.py:61`) and copes
with the answer "not installed".

**The `ctypes` stand-in has one function.** `recipes/ctypes_stub.py` defines `WinError` and
nothing else, because pandas imports `ctypes` unconditionally (`pandas/errors/__init__.py:8`)
and uses only that. numpy imports it too (`numpy/_core/_internal.py:20`), in a `try`. Other
importers need more names at import time, and fail:

| importer | what it needs at import | today |
|---|---|---|
| sympy 1.14.0 (`sympy/external/gmpy.py:3`) | `c_long`, `sizeof` | `ImportError: cannot import name 'c_long'` (EXECUTED by the memo) |
| threadpoolctl 3.7.0 (`threadpoolctl.py:56`) | `c_uint32` and the other fixed-width types, `Structure`, `c_char_p`, `c_void_p`, `DEFAULT_MODE`, `ctypes.util.find_library` | `AttributeError: … no attribute 'c_uint32'` (EXECUTED by the memo) |
| pandas 3.0.6 (`pandas/io/clipboard/__init__.py:51`), in today's zip | `c_size_t`, `c_wchar`, `c_wchar_p`, `get_errno`, `sizeof` | `ImportError: cannot import name 'c_size_t'` (EXECUTED by the review) |

sympy and threadpoolctl are tier A (approved, decision 43), and scikit-learn imports
threadpoolctl. pandas' clipboard module is in today's zip. Each would import with a stand-in
that names the C types and refuses every foreign call.

**One trap the stand-in must avoid.** numpy turns a type into a dtype in three steps
(`descriptor.c:94-136`, READ by the review):
1. it asks the type for `__numpy_dtype__` (or `dtype`);
2. it asks whether the type's base class comes from `_ctypes`;
3. otherwise it treats the type as a plain Python class, which is `dtype('O')`.

A stand-in type that answers neither question becomes `object` in numpy, with no error. The
review ran it: `np.dtype(ctypes.c_double)` gave `dtype('O')`, and
`np.asarray([1.5], dtype=ctypes.c_double)` returned an object array (EXECUTED). That is a
silent wrong answer, and it would disguise the platform (§4.11). Decision 5 closes it.

## Decisions

1. **A wheel keeps exactly two files of its `.dist-info`: `METADATA` and `entry_points.txt`.**
   `wheel_members` yields `<name>-<version>.dist-info/METADATA` and, when the wheel has one,
   `<name>-<version>.dist-info/entry_points.txt`. It uses the folder name the wheel gives them
   and keeps their bytes unchanged. Everything else in `.dist-info` stays out:
   - `RECORD`: it lists `.py` files and their hashes, and the zip holds `.pyc` files instead, so
     it would be false.
   - `WHEEL`, `INSTALLER`, `REQUESTED`, `direct_url.json`, `zip-safe`: facts about an install,
     which this zip is not.
   - `top_level.txt`: only `importlib.metadata.packages_distributions()` reads it, and every
     member costs every plain start (Decision 7). Left out.
   - Licence files (`LICENSE`, `licenses/…`): Decision 4.

   The `.data` folder stays out, as today. A top-level `.egg-info` folder in a wheel is dropped
   too (no pinned wheel has one; Decision 3). This is the memo's tested set (`followup.tsv`:
   73 members for 58 distributions).
2. **A package built from its sdist gets its `METADATA` from the sdist's `PKG-INFO`.** A new
   option, `make_stdlib_zip.py --metadata <PKG-INFO>`, packs that file, bytes unchanged, as
   `<name>-<version>.dist-info/METADATA`.
   - The name and version come from the file's own `Name:` and `Version:` headers. The name is
     written as a wheel's folder name is: runs of `-`, `_` and `.` become one `_`, in lower case.
   - A file without exactly one `Name:` and one `Version:` header before its first blank line
     stops the build with one line naming the file.
   - Step 70 passes `--metadata "$B/numpy-2.5.2/PKG-INFO"` and
     `--metadata "$B/pandas-3.0.6/PKG-INFO"`.

   **Why `PKG-INFO`.** It is the project's own core metadata, in the same format as `METADATA`
   (numpy's is Metadata-Version 2.4, pandas' 2.1; READ). It sits in the pinned tarball. The
   build tree's copies equal a fresh extraction of the pinned tarballs (EXECUTED by the review:
   `cmp`). The one carried patch does not touch them (READ), and spec 020's check judges the
   whole tree. So it is pinned bytes, the same on every host. numpy's says `Version: 2.5.2`
   while its tree carries one recorded patch. That equals `numpy.__version__`, and the patch is
   recorded in `MANIFEST` and the CHANGELOG, so nothing changes for it.

   **No `entry_points.txt` for these two.** Their entry points live in `pyproject.toml` (READ):
   - numpy's are two console scripts and the `pkg_config`, `array_api` and `pyinstaller40`
     groups. None of them means anything in the guest.
   - pandas' one is `pandas_plotting_backends: matplotlib`. pandas loads its matplotlib backend
     by name before it looks at entry points (`pandas/plotting/_core.py:2177`, READ).

   Generating the file from `pyproject.toml` would be new code for nothing a guest uses.
3. **A tree never brings metadata of its own.**
   - `walk` skips every `.dist-info` folder, as today, and now every `.egg-info` folder too.
     `importlib.metadata` reads both kinds, and an `.egg-info` would be a second route to
     metadata, with `SOURCES.txt` beside it.
   - A new function, `tree_members(tree)`, is what `main` calls for each `--tree`. Before it
     walks, it stops the build when the tree holds a `.dist-info` or `.egg-info` folder at its
     top. The stop is one line: `<tree>: <folder> holds package metadata; pass the package as a
     wheel, or its sdist's PKG-INFO with --metadata`. So a tree's metadata is never lost or
     smuggled in unnoticed.
   - Today's two trees and the sdists hold neither kind, and today's zip has no `.egg-info`
     member (EXECUTED: `find build/numpy-install build/pandas-install build/numpy-2.5.2
     build/pandas-3.0.6 -maxdepth 4 -name '*.egg-info'` finds nothing; `unzip -Z1` counts 0).
     So the build does not stop, and no member is lost.
   - This matters for spec 023: Pillow and kiwisolver are setuptools sdists and often carry
     `<name>.egg-info/` (INFERRED by the review; they are not pinned yet).
4. **Licence notices stay where they are.** The licence files inside `.dist-info` are not packed.
   - Notices ship in the artifact set's `LICENSES/`, one file per component, built by
     `assemble_artifacts.py` from the pinned wheels and sources (specs 004 and 009). That is
     unchanged.
   - `METADATA`'s `License:`, `License-Expression:` and `License-File:` headers name the
     licence. The files those headers name are not in the zip.
5. **The `ctypes` stand-in becomes a small package. It names and sizes C types, gives numpy the
   dtype numpy would give a real one, and refuses every foreign call.**

   **Where it lives.**
   - `recipes/ctypes_stand_in/__init__.py`, `_types.py` and `util.py` are packed as
     `ctypes/__init__.py`, `ctypes/_types.py` and `ctypes/util.py`, compiled to `.pyc` as every
     module is.
   - `recipes/ctypes_stub.py` is deleted.
   - The recipe folder is not named `ctypes`, so nothing on a host can import it by accident.
   - CPython's own `ctypes` stays out (`--skip ctypes`): wasi-sdk has no libffi, and the guest
     has no `_ctypes`.

   **Built on first use.** At import the module defines only:
   - `__getattr__` and `__dir__` (PEP 562), and an `__all__` naming every public name, so
     `from ctypes import *` gets them all;
   - `DEFAULT_MODE`, `RTLD_GLOBAL`, `RTLD_LOCAL`;
   - `WinError`.

   The first lookup of any other public name imports `ctypes._types`. That module builds the
   whole table at once, and `__getattr__` stores the result in `ctypes`' globals. Later lookups
   are plain attribute reads. numpy and `pandas.errors` only `import ctypes`, so they never pay
   for the types.

   **The builder lives outside `ctypes/__init__`** (the confirmation's condition 1).
   `ctypes/__init__` stays a few dozen lines: the names above and an `__all__`. All the builder's
   code is in `ctypes/_types.py`: the types, the aliases, `sizeof`, `POINTER`, `CFUNCTYPE`, the
   libraries and the memory functions. This costs one more member. It was measured, unlike
   the alternative (a private function in `ctypes/util.py`, no new member, INFERRED only).
   `__init__` imports neither `_types` nor `util` at import. The confirmation measured why
   (EXECUTED, Decision 7):
   - building the types eagerly cost about +7.2 M fuel on every plain `import numpy`;
   - a lazy builder kept inside `__init__` still cost +2.9 M there and +0.23 M on every snapshot
     call, because numpy and pandas load that larger module (and the snapshot holds it) even
     though the types are never built.

   **The simple types, as CPython makes them on wasm32** (`Lib/ctypes/__init__.py`, READ by the
   review).
   - Classes, each with CPython's `_type_` code:

     | type | code | type | code | type | code |
     |---|---|---|---|---|---|
     | `c_bool` | `?` | `c_char` | `c` | `c_wchar` | `u` |
     | `c_byte` | `b` | `c_ubyte` | `B` | `c_short` | `h` |
     | `c_ushort` | `H` | `c_long` | `l` | `c_ulong` | `L` |
     | `c_longlong` | `q` | `c_ulonglong` | `Q` | `c_float` | `f` |
     | `c_double` | `d` | `c_longdouble` | `g` | `c_char_p` | `z` |
     | `c_wchar_p` | `Z` | `c_void_p` | `P` | | |

   - Aliases, made by CPython's rule from `struct.calcsize` in the guest, not from a table:
     - `c_int` and `c_uint` are `c_long` and `c_ulong` when `int` and `long` have one size;
       otherwise they are classes (`i`, `I`).
     - `c_longlong` and `c_ulonglong` are `c_long` and `c_ulong` when `long` and `long long`
       have one size.
     - `c_longdouble` is `c_double` when they have one size.
     - `c_size_t` and `c_ssize_t` are the first of (`c_uint`, `c_int`), (`c_ulong`, `c_long`),
       (`c_ulonglong`, `c_longlong`) whose size is the pointer's.
     - `c_int8` is `c_byte`, and `c_uint8` is `c_ubyte`.
     - Each other `c_intN` is the last of `c_short`, `c_int`, `c_long`, `c_longlong` of N/8
       bytes. Each `c_uintN` is the same among the unsigned four.
     - `c_time_t` is `c_int64`: WASI's `time_t` is 8 bytes (`SIZEOF_TIME_T` is 8 in the build's
       `_sysconfigdata`, READ).

     On wasm32 that gives: `c_int is c_long`, `c_uint is c_ulong`, `c_size_t is c_ulong`,
     `c_ssize_t is c_long`, `c_int16 is c_short`, `c_int32 is c_long`, `c_int64 is c_longlong`.
     So `POINTER(c_int) is POINTER(c_long)`, as in a real wasm32 `ctypes`.
   - `sizeof` of a simple type is `struct.calcsize(_type_)` where `_type_` is a `struct` code.
     The pointer types (`z`, `Z`, `P`) take `struct.calcsize("P")`. `c_wchar` is 4 (WASI's
     `wchar_t` is 32-bit). `c_longdouble` is 16 (wasm32's 128-bit `long double`, which step 40
     already checks for numpy). The guest check compares every size with the guest's own
     `sysconfig` (Decision 8).

   **numpy's dtypes.**
   - Every simple type has a class-level `__numpy_dtype__`. It returns
     `sys.modules["numpy"].dtype(cls._type_)`: exactly what numpy computes for a real ctypes
     simple type (`numpy/_core/_dtype_ctypes.py`, `_from_ctypes_scalar`). It is a fact about
     the type, not a foreign call. numpy is loaded whenever numpy asks.
   - Each numeric simple type (codes `?`, `b`, `B`, `h`, `H`, `l`, `L`, `q`, `Q`, `f`, `d`,
     `g`) has `__ctype_le__`, which is the type itself on little-endian wasm32, and
     `__ctype_be__`:
     - for a one-byte type, the type itself;
     - for a wider one, a big-endian twin. The twin's `__numpy_dtype__` is
       `dtype(">" + code)`, its `__ctype_be__` is itself, and its `__ctype_le__` is the native
       type. This is how numpy's `_from_ctypes_scalar` reads a real twin.

     `numpy.ctypeslib.as_ctypes_type` reads these (`_ctypeslib.py:394`).
   - Every other stand-in type has a `__numpy_dtype__` that raises the `OSError`: `Structure`
     and `Union` subclasses, `POINTER(…)`, `CFUNCTYPE(…)` and array types. The stand-in
     computes no layouts. Without the attribute, numpy would fall back to `dtype('O')`.

     The review's prototype gave `c_double` → `float64`, `c_long` → `int32`,
     `c_longdouble` → `float128` and `c_void_p` → `uint32`. With it, `hasattr(np, "ctypeslib")`
     is `True` and `inspect.getmembers(np)` works (EXECUTED, its `dt` variant). A
     `__numpy_dtype__` that raised for the simple types too was tried and rejected:
     `import numpy.ctypeslib` then raises `OSError`, which `hasattr(np, "ctypeslib")` does not
     catch (EXECUTED, its `fix` variant).

   **Other types and factories.**
   - `Structure` and `Union` can be subclassed with `_fields_`, so a module that declares a C
     struct at import still imports.
   - `POINTER(t)` returns one stand-in type per `t`, the same object each time.
   - `CFUNCTYPE(restype, *argtypes)` and `PYFUNCTYPE` return a stand-in type.
   - **Array types:** `t * n` and `n * t` return a stand-in array type, with `_type_` set to
     `t` and `_length_` to `n`. So `_fields_ = [("name", c_char * 16)]` declares at import, as
     it does in CPython. Without this, `c_char * 4` raised `TypeError` (EXECUTED by the review).

   **Libraries.** `CDLL`, `PyDLL`, `LibraryLoader`, `cdll`, `pydll`, `DEFAULT_MODE`,
   `RTLD_GLOBAL`, `RTLD_LOCAL`.

   **`ctypes.util.find_library(name)`** returns `None` for every name: the guest has no shared
   library to find.

   **`WinError`**, as today.

   **The rule.** A name exists so that an import succeeds. Declaring a type works:
   - a simple type, a `Structure` or `Union` subclass with `_fields_`;
   - `POINTER(t)`, `CFUNCTYPE(…)`, `t * n`.

   Anything that would load a library, touch memory or make an instance raises
   `OSError("ctypes is unavailable on wasm32-wasi")`, today's message. That covers:
   - **loading any library:** `CDLL(…)` with any name, `None` included, and
     `cdll.LoadLibrary(…)`, `cdll.<name>` and `cdll[<name>]`;
   - **instantiating any stand-in type:** a simple type, a `Structure` or `Union` subclass, a
     pointer, array or function type. So `@CFUNCTYPE(c_int, c_int)` on a module-level `def`
     raises `OSError` at import time (see "The edges" below);
   - **the classmethods on every stand-in type:** `from_buffer`, `from_buffer_copy`,
     `from_address`, `from_param`, `in_dll`;
   - **the memory functions:** `byref`, `pointer`, `cast`, `addressof`, `memmove`, `memset`,
     `string_at`, `wstring_at`, `create_string_buffer`, `create_unicode_buffer`, `resize`,
     `get_errno`, `set_errno`;
   - **`__numpy_dtype__` of a non-simple type** (above).

   `OSError` is what CPython's `ctypes` raises when a library cannot be loaded. So code that
   copes with a missing library copes with this one.

   **`sizeof`.**
   - It answers for:
     - a simple type;
     - a pointer type or a function type: the pointer size;
     - an array type: `_length_` × the element's size.

     Each of these is a true fact on wasm32.
   - It raises the `OSError` for a `Structure` or `Union` subclass: the stand-in computes no
     layouts.
   - It raises `TypeError` for anything that is not a stand-in type, as CPython does.

   **The edges, stated.** Code that would call C fails, as it must, but it fails in one of two
   places:
   1. **At first use.** This is the common case: a `CDLL` in a function, as in threadpoolctl.
   2. **At import.** A module that makes an instance at import fails there: a callback made by
      decorating a module-level `def` with `CFUNCTYPE`, or a module-level `c_int(0)`. Such a
      module raises `OSError` at import, not `ImportError`. An importer that guards with
      `except ImportError` does not catch it.

   This is accepted. No importer named here does it. A callback object that exists but cannot be
   called would disguise the platform.

   **Why a stand-in that refuses, not more.** A stand-in that made instances (`c_int(3).value`)
   would mimic `ctypes` without its truncation or its memory, and would disguise the platform
   (§4.11). Naming types, sizing them and giving numpy their dtypes is true on wasm32. Nothing
   more is claimed.
6. **threadpoolctl's own stand-in is deferred to the tier-A specification.**
   - threadpoolctl is not in today's zip. Its only user in the approved profile is
     scikit-learn (tier B).
   - With Decision 5, the real threadpoolctl imports. Its `threadpool_info()` then raises the
     stand-in's `OSError`, because it loads libc through `ctypes.CDLL(find_library("c"))`
     (`threadpoolctl.py`, `_get_libc`, READ in 3.6.0's source).
   - The tier-A specification chooses between that and a small stand-in module of ours that
     reports no native thread pools, with scikit-learn's calls in view. The memo leans to the
     stand-in (INFERRED there).
   - Adding a module named `threadpoolctl` now would put a package in the guest that nothing in
     it uses.
7. **What it costs, stated so growth can be told from regression.**

   **Members.** Today's zip has 1,751 members (EXECUTED: `unzip -Z1
   build/artifacts/python-stdlib.zip | wc -l`). This change adds:
   - five `METADATA` members: numpy and pandas from `PKG-INFO`, and python-dateutil, tzdata and
     six from their wheels. None of the three wheels has an `entry_points.txt` (READ:
     `unzip -Z1`);
   - two more for `ctypes`: `ctypes.pyc` becomes `ctypes/__init__.pyc`, `ctypes/_types.pyc` and
     `ctypes/util.pyc`.

   That makes **1,758 members, +7** (EXECUTED by the confirmation's `standin-split` zip).

   **Fuel and bytes.** All EXECUTED by the review's confirmation, through the judge's own
   driver, on its `standin-split` prototype against today's set. That prototype is Decision 5 as
   now written: lazy types, the builder in `ctypes/_types.py`, the dtypes, twins, array types and
   aliases.

   | what | today | growth |
   |---|---|---|
   | plain `-c pass` | 241,460,846 | +542,066 (+0.22%; 7 members at about 77,400 each) |
   | plain `import numpy` | 1,127,820,357 | +983,668 (+0.09%) |
   | plain `import pandas` | 4,987,229,727 | +835,650 (+0.02%) |
   | snapshot `-c pass` | 81,962,284 | +154,670 (+0.19%) |
   | snapshot pandas groupby | 87,200,200 | +142,254 (+0.16%) |
   | snapshot CSV-and-groupby program | | +16,277 |
   | the zip | 11,140,635 bytes | +20,532 bytes |
   | the snapshot | 65,506,824 bytes | +7,285 bytes |

   The five golden jobs on the plain binary grew as follows (EXECUTED, the confirmation's
   `jobs.py`):

   | job | growth |
   |---|---|
   | `numpy_csv` | +1,146,557 |
   | `pandas_csv` | +2,765,223 (+0.05%, the largest share) |
   | `numpy_random` | +231,520 |
   | `compress` | +764,393 |
   | `sqlite` | +701,298 |

   In none of these runs were the stand-in's types built (EXECUTED: a copy of `numpy_random`
   printing `'c_long' in vars(ctypes)` prints `False`). On a 4 to 6 G-fuel program, the
   collector's timing moves fuel by a few M whenever the heap's contents change (INFERRED by
   the confirmation: a two-line tail alone moved `numpy_random` by several M). Criterion 4's
   caps are built around that.

   - The ratchet's tolerance is 0.01%, so every plain check and every snapshot check grows past
     it.
   - For the metadata members alone (the review's `meta` variant): +400,825 on plain `-c pass`,
     +308,504 on plain `import numpy`, +87,744 on snapshot `-c pass`.
   - Eager types would have cost about +7.2 M more on every plain `import numpy` (the review's
     eager variant: +7,812,307). A lazy builder kept in `__init__` would have cost
     +2,889,359 there and +230,914 on snapshot `-c pass` (the confirmation's `standin-full`).
     So the builder lives in `ctypes/_types.py`.
   - **The snapshot's growth is not fully explained.** The snapshot holds a zip directory seven
     entries longer, and its heap moves. Its finalization, which tears the heap down, is about
     97% of a snapshot `-c pass` (spec 021). That is the likely cause (INFERRED, as spec 021
     found for its own moves). The review did not profile it, and neither did this
     specification.
   - The builder measures the real stand-in against criterion 4's caps.
   - `python.wasm` does not change: step 60 is untouched.

   **With tier A** the rule adds about one or two members per distribution. The memo measured
   73 for 58 distributions, +6.0 M fuel on a plain start (`followup.tsv`, EXECUTED).

   **A metadata lookup's own cost.** Measured on the snapshot by the review (EXECUTED; its
   `imd`, `v1`, `v2`, `nt` rows):
   - `import importlib.metadata` costs about 35 M over `pass`, as today.
   - The first `version("numpy")` in a process then costs about 361 M more: 478.1 M in all
     against 336.2 M today, when the same call fails.
     - About 219 M of it is the scan of the zip's directory through `zipfile.Path`. Today's zip
       pays that already, for a lookup that finds nothing.
     - About 142 M is new: reading and parsing the `METADATA` it now finds.
   - A second lookup in the same process costs about 23 M more. CPython 3.15 caches the scan per
     path and modification time (`importlib/metadata/__init__.py`: `FastPath.__new__`'s
     `lru_cache` and `lookup`'s `method_cache`, READ).
   - **`import numpy.testing` on the snapshot costs +136 M** (464,071,491 to 600,137,174, +29%).
     numpy now finds its distribution and reads it (`numpy/testing/_private/utils.py:61`). It
     gains nothing from it: `IS_INSTALLED` stays `False`, because `locate_file` returns a
     `zipfile.Path`, not numpy's folder (`utils.py:87`, READ by the review).
     `np.testing.assert_allclose` is common in generated code, so this is a real cost. No judge
     check imports `numpy.testing` today (READ: `grep`), so the ratchet does not see it. The
     README states it.
   - **Programs that never ask for metadata pay nothing here.** That includes every `import
     numpy` and `import pandas`: neither imports `importlib.metadata` or `numpy.testing`
     (EXECUTED by the review: `sys.modules` after the imports, on both binaries). So step 80's
     pre-import freezes no cached lookup into the snapshot.

   **What spec 035 recovers.** Spec 035, "the zip's directory is read once" (in pre-build
   review; it lands after this one, question 57), replaces `importlib.metadata`'s zip search.
   - Its part 3 wraps `PathFinder.find_distributions` and answers `FastPath.zip_children` from
     the directory zipimport already holds. Its own table puts a metadata miss on the snapshot at
     about 10 M, against 218.9 M today (its Decision 7 and check 6). So **035 recovers the
     ~219 M scan**, today's cost and this change's alike.
   - It also reads `METADATA` through its own path type rather than `zipfile.Path` (its
     Decision 7).
   - **Whether it recovers the ~142 M of reading and parsing is not known.** The parse of the
     `METADATA` text is not what 035 replaces. The same holds for `numpy.testing`'s +136 M.
   - 035's builder measures `version("numpy")` and `import numpy.testing` on the snapshot with
     this change in, and records what remains in 035's landing notes.

   Keeping numpy's `METADATA` is still right. Tier A needs the rule for every distribution, and
   a true answer to `version("numpy")` is worth more than a fast wrong one.
8. **The checks** (Design). Two guest checks go in v1.3, each on both binaries.

   **`test_packages_carry_their_metadata`.**
   - `importlib.metadata.version` gives MANIFEST's version for numpy and pandas, equal to
     `numpy.__version__` and `pandas.__version__`.
   - The guest's `importlib.metadata.distributions()` is exactly python-dateutil, tzdata, six,
     numpy and pandas, each at its MANIFEST version. A later specification that adds a package
     adds it to this set.
   - `importlib.metadata.files("numpy")` is `None`, because `RECORD` is not kept, and the check
     says so.
   - Seen failing first: today `version("numpy")` raises `PackageNotFoundError`.

   **`test_ctypes_stand_in_names_what_packages_import`.**
   - `import pandas.io.clipboard` succeeds. Seen failing first: today it raises `ImportError`
     on `c_size_t`.
   - These import-time names resolve. They are written by name in the check, not copied from
     either package:
     - sympy's: `from ctypes import c_long, sizeof`;
     - threadpoolctl's: the fixed-width types, `c_char_p`, `c_void_p`, `Structure` subclassed
       with `_fields_` (one field `c_char * 16`), `DEFAULT_MODE`, and
       `from ctypes.util import find_library`.
   - **Sizes.** `sizeof` of each simple type equals the guest's
     `sysconfig.get_config_var("SIZEOF_…")`. The build's `_sysconfigdata` has each (READ):

     | `SIZEOF_…` | types |
     |---|---|
     | `_BOOL` | `c_bool` |
     | `SHORT` | `c_short` |
     | `INT` | `c_int` |
     | `LONG` | `c_long` |
     | `LONG_LONG` | `c_longlong` |
     | `SIZE_T` | `c_size_t` |
     | `VOID_P` | the three pointer types and `POINTER(c_int)` |
     | `WCHAR_T` | `c_wchar` |
     | `FLOAT` | `c_float` |
     | `DOUBLE` | `c_double` |
     | `LONG_DOUBLE` | `c_longdouble` |
     | `TIME_T` | `c_time_t` |

     The fixed-width types' sizes are their widths, and `sizeof(c_char * 16) == 16`.
   - **Aliases.** `c_int is c_long` and `c_int32 is c_long` (Decision 5).
   - **numpy's dtypes.** Each seen failing first with today's stub (`AttributeError`) and with
     a mutant stand-in that lacks `__numpy_dtype__` (`dtype('O')`):
     - `np.dtype(ctypes.c_double) == np.float64`;
     - `np.dtype(ctypes.c_long) == np.int32`;
     - `np.dtype(ctypes.c_int32.__ctype_be__) == np.dtype(">i4")`;
     - `np.ctypeslib.as_ctypes_type(np.int32) is ctypes.c_long`;
     - `hasattr(np, "ctypeslib")` is `True`, and does not raise.
   - **Refusals.** Each of these raises `OSError` with Decision 5's message:
     - `np.arange(3).ctypes`, which makes a `c_void_p`;
     - pandas' `pd.api.interchange.from_dataframe(df.__dataframe__())` on a small integer
       frame, which reaches `ctypes.cast`. Today it raises `AttributeError`. A stand-in
       without twins raises a misleading `NotImplementedError` or `AttributeError` (EXECUTED
       by the review);
     - `CDLL(None)`, `c_int(1)`, an instance of the `Structure` subclass, `byref`,
       `c_int.from_buffer(b"")`, and `np.dtype` of the `Structure` subclass.
   - **Unchanged edges.** `ctypes.WinError()` still raises `OSError`. `import ctypes.wintypes`
     raises `ImportError`.
   - Seen failing first: today `c_long` is missing.

   The real sympy, threadpoolctl and tabulate imports, and `df.to_markdown()`, are checked by
   the tier-A specification, which puts those packages in the zip.

   Unit checks in `tests/unit/test_build_scripts.py` cover the zip builder and the stand-in on
   the host (Design).
9. **Ordering with other build-class work.** This specification and spec 023 (matplotlib M1)
   both change step 70, so they never build at once (§5.7). Whichever lands second applies this
   one's rule to the other's packages. Every Python distribution in the zip gets its `METADATA`:
   - a pinned wheel through `--wheel`, automatically;
   - a package built from its sdist (matplotlib, kiwisolver, Pillow) through `--metadata` with
     that sdist's `PKG-INFO`. If its tree holds an `.egg-info`, Decision 3 stops the build until
     step 70 leaves that folder out of the tree.

   That distribution then joins the set in `test_packages_carry_their_metadata`.

   Spec 035 changes no file this one changes (it changes step 60 and the reactor). It plans to
   land after this one. Its part 3 must keep `test_packages_carry_their_metadata` passing, as
   its own text says.
10. **What the change does to the artifact set.**
    - The zip changes: seven new or moved members, everything else byte for byte.
    - The snapshot changes with it. `python.wasm` does not change.
    - `MANIFEST`'s `recipe` lines change for `scripts/make_stdlib_zip.py` and
      `scripts/steps/70_zip.sh`. `recipes/ctypes_stub.py`'s line is replaced by the three
      `recipes/ctypes_stand_in/` lines.
    - `SHA256SUMS` changes in the zip's, the snapshot's and `MANIFEST`'s lines.
    - The `-V` banner keeps "no ctypes": no foreign function can be called, which is what it
      says (question 58). The README explains what the stand-in does (Design).

## Intent

A package that asks for its own version, its entry points, a C type's size or a C type's numpy
dtype gets a true answer from the zip. A package that tries to call C gets the `OSError` it
would get on a machine without the library.

## Design

| file | change |
|---|---|
| `scripts/make_stdlib_zip.py` | `wheel_members` keeps `METADATA` and `entry_points.txt`, and drops a top-level `.egg-info` (Decision 1); `--metadata` and a function `sdist_metadata(path) -> (bytes, member name)` (Decision 2); `walk` skips `.egg-info`; `tree_members(tree)`, which `main` calls for each `--tree` (Decision 3); the docstring's usage line |
| `scripts/steps/70_zip.sh` | two `--metadata` lines; three `--file` lines for `ctypes/__init__.py`, `ctypes/_types.py` and `ctypes/util.py` replace the `ctypes.py` one |
| `recipes/ctypes_stand_in/__init__.py` | new (Decision 5): the constants, `WinError`, `__all__`, and a `__getattr__` and `__dir__` that import `._types` on the first type lookup; nothing else |
| `recipes/ctypes_stand_in/_types.py` | new (Decision 5): every type, alias, factory, library and memory function, built from a table of names and codes, with the aliases from `struct.calcsize` |
| `recipes/ctypes_stand_in/util.py` | new: `find_library`, returning `None` |
| `recipes/ctypes_stub.py` | deleted |
| `tests/checks/test_v1_3_data_stack.py` | `test_packages_carry_their_metadata[plain, snapshot]`, `test_ctypes_stand_in_names_what_packages_import[plain, snapshot]` (Decision 8) |
| `tests/unit/test_build_scripts.py` | the unit checks below |
| `README.md` | the recipe paragraph (now "one-function stand-ins for `ctypes` and `mmap`") describes the `ctypes` package; the platform paragraph gains sentences on the points listed after this table |
| `CHANGELOG.md` | under 0.1.0a4: the zip keeps package metadata; the wider `ctypes` stand-in |

The README's platform paragraph gains these points:
- `importlib.metadata` gives each package's name, version and entry points, and `files()`
  gives `None`.
- The first metadata lookup in a process costs about 0.36 G fuel on the snapshot, and
  `import numpy.testing` about 0.14 G more than before, until spec 035 lands.
- `import ctypes` works: it sizes wasm32's C types and gives numpy their dtypes, but it loads
  no library and calls nothing (`OSError`).

Unit checks, each seen failing first against today's scripts or stub:

- `test_the_zip_keeps_a_wheels_metadata_and_entry_points`. A temporary wheel holds:
  - a module and a `.data/` file;
  - an `x.egg-info/PKG-INFO`;
  - a `.dist-info/` with `METADATA`, `entry_points.txt`, `RECORD`, `WHEEL`, `INSTALLER`,
    `REQUESTED`, `direct_url.json`, `top_level.txt`, `zip-safe` and `licenses/LICENSE`.

  `wheel_members` yields the module, `METADATA` and `entry_points.txt`, with their bytes
  unchanged, and nothing else. Today it yields the module and the `.egg-info` file.
- `test_an_sdists_pkg_info_becomes_metadata`.
  - A `PKG-INFO` with `Name: Foo.Bar-baz` and `Version: 1.0` becomes
    `foo_bar_baz-1.0.dist-info/METADATA`, with its bytes unchanged.
  - One without `Name:`, one without `Version:`, and one with two `Version:` headers each stop
    with one line naming the file.
  - Today the function does not exist.
- `test_a_tree_with_package_metadata_stops_the_zip`.
  - It calls `make_stdlib_zip.tree_members` directly, as `test_the_zip_walk_skips_litter` calls
    `walk`. `main` cannot run on the judge's Python: it requires the line's 3.15, and the
    judge's is 3.14 (the review, EXECUTED).
  - A tree with `x-1.0.dist-info/` at its top stops with Decision 3's exact line. So does one
    with `x.egg-info/` at its top.
  - A tree with `pkg/y.egg-info/` deeper down yields `pkg`'s modules and no `.egg-info` file.
  - Today `tree_members` does not exist, and `walk` yields the nested `.egg-info` file.
- `test_the_ctypes_stand_in_names_and_refuses`. The recipe folder is loaded on the host as a
  package under a private name, never as `ctypes`, so that `__init__`'s relative import of
  `._types` resolves.
  - Before any lookup, the package's globals hold none of the type names, and its `_types`
    submodule is not in `sys.modules`. Every Decision 5 name then resolves, and after the first
    lookup the types are in the package's globals.
  - `CDLL(None)`, `CDLL("libc.so")`, `cdll.LoadLibrary("x")`, `cdll.x` and `cdll["x"]` each
    raise `OSError` with the message.
  - So do: an instance of each simple type, of a `Structure` subclass, of `c_char * 4` and of a
    `CFUNCTYPE` type; each listed classmethod; and each memory function.
  - `c_char * 4` and `4 * c_char` are types with `_length_` 4.
  - `POINTER(c_char) is POINTER(c_char)`. `CFUNCTYPE(c_int, c_char_p)` is a type.
  - `sizeof(c_wchar) == 4`, `sizeof(c_longdouble) == 16`, and `sizeof` of a `Structure`
    subclass raises `OSError`. `sizeof(3)` raises `TypeError`.
  - `c_int8 is c_byte`, and each numeric type's `__ctype_le__` is itself.
  - `util.find_library("c") is None`.
  - The sizes and aliases taken from `struct` are checked in the guest, not here, because the
    host's `long` is not wasm32's. numpy's dtypes are checked in the guest too.
  - Today's stub fails at `c_long`.

## Scope

In: the above. Out:

- **Real sympy, threadpoolctl, tabulate and markdown in the zip,** with their judge jobs: the
  tier-A specification, after "the zip's directory is read once" (decisions 44 and 45).
- **threadpoolctl's stand-in:** the tier-A specification (Decision 6).
- **`numpy.ctypeslib` and `ndarray.ctypes`.** This change changes how they behave:
  - `import numpy.ctypeslib` now succeeds. Today it raises `AttributeError` on `c_long`.
  - `as_ctypes_type` gives the right stand-in type for a scalar dtype.
  - `as_ctypes`, `as_array`, `ndpointer(…).from_param`, `load_library` and `ndarray.ctypes`
    raise the stand-in's `OSError`, since each makes an instance, touches memory or loads a
    library. Today they raise `AttributeError`.

  Only the cases Decision 8 names are checked.
- **`np.dtype` of a `Structure`, an array type or a pointer type:** it raises the `OSError`
  rather than computing numpy's structured or subarray dtype. The stand-in computes no layouts.
- **`df.to_clipboard()` and `pd.read_clipboard()`.** Their module now imports, and
  `read_clipboard()` raises pandas' "could not find a copy/paste mechanism" error (EXECUTED by
  the review). It is not checked: a clipboard means nothing in a sandbox.
- **`multiprocessing.sharedctypes`** now imports. Its first use reaches the stand-in's or the
  `mmap` stand-in's `OSError` (INFERRED by the review). Not checked.
- **Struct layouts and `sizeof` of a `Structure`:** no importer named here needs them.
- **`top_level.txt`, `RECORD` and `importlib.metadata.packages_distributions()`** (Decision 1).
- **Entry points for numpy and pandas** (Decision 2).
- **Any change to zipimport, `zipfile`, `importlib.metadata`, or the per-member or per-read
  cost:** spec 035, "the zip's directory is read once" (Decision 7).

## Acceptance criteria

1. **The checks.** The four unit checks and the two guest checks exist, and each was seen
   failing first as Decision 8 and Design say:
   - today's set fails the guest checks with `PackageNotFoundError` for numpy, and with
     `ImportError` on `c_size_t` and `c_long`;
   - the dtype assertions also fail against a mutant stand-in without `__numpy_dtype__`
     (`dtype('O')`), recorded in the landing notes.
2. **The zip's names and bytes.** A full build from pins in a clean clone gives a `python.wasm`
   byte for byte the same as today's (`cmp`). The builder runs these commands from the clone's
   root, with today's set copied to `$OLD` first, and records their output in the landing
   notes.
   - **Names:**
     ```sh
     diff <(unzip -Z1 "$OLD/python-stdlib.zip" | LC_ALL=C sort) \
          <(unzip -Z1 build/artifacts/python-stdlib.zip | LC_ALL=C sort)
     ```
     The diff shows exactly:
     - `< ctypes.pyc`;
     - `> ctypes/__init__.pyc`, `> ctypes/_types.pyc` and `> ctypes/util.pyc`;
     - `> numpy-2.5.2.dist-info/METADATA`, `> pandas-3.0.6.dist-info/METADATA`,
       `> python_dateutil-2.9.0.post0.dist-info/METADATA`, `> six-1.17.0.dist-info/METADATA`
       and `> tzdata-2026.5.dist-info/METADATA`.

     That is 1,758 names.
   - **Shared members, byte for byte:**
     ```sh
     uv run --no-project python -I -c 'import sys, zipfile
     a, b = (zipfile.ZipFile(p) for p in sys.argv[1:])
     shared = sorted(set(a.namelist()) & set(b.namelist()))
     bad = [n for n in shared if a.read(n) != b.read(n)]
     print(len(shared), "shared;", len(bad), "differ:", bad[:5])' \
       "$OLD/python-stdlib.zip" build/artifacts/python-stdlib.zip
     ```
     It prints `1750 shared; 0 differ: []`.
   - **`METADATA` against its source:** each of the five `cmp`s exits 0:
     ```sh
     Z=build/artifacts/python-stdlib.zip
     cmp <(unzip -p $Z numpy-2.5.2.dist-info/METADATA) build/numpy-2.5.2/PKG-INFO
     cmp <(unzip -p $Z pandas-3.0.6.dist-info/METADATA) build/pandas-3.0.6/PKG-INFO
     for w in python_dateutil-2.9.0.post0 six-1.17.0 tzdata-2026.5; do
       cmp <(unzip -p $Z "$w.dist-info/METADATA") \
           <(unzip -p downloads/$w-py2.py3-none-any.whl "$w.dist-info/METADATA")
     done
     ```
3. **The same bytes everywhere.**
   - **Every host.** A manual run of the release workflow on the reviewed commit
     (`gh workflow run release.yml --ref <branch>`; a manual run is a dry run) passes its
     `rebuild` and `same-bytes` jobs. Those jobs `cmp` each host's `SHA256SUMS` with the build's
     (spec 012, Decision 7). Its run number goes in the landing notes.
   - **Again, with litter.** Steps 70 to 90, re-run with a `.DS_Store` in
     `build/pandas-install/pandas/`, in numpy's installed package and beside each `PKG-INFO`
     (spec 018's criterion), give the same `SHA256SUMS` again (`cmp`).
4. **The judge.** `uv run pytest` is green with `--accept "<reason>"`,
   `--accept-judge "<the new checks>"` and `--accept-growth "<the account>"`, and loses no pass.
   - **The account** cites the build's own measured numbers, metric by metric, each against the
     confirmation's figure (Decision 7) and the cap below. The caps follow the confirmation's
     condition 2: absolute where fuel is stable, relative where the collector's timing moves it.
     A growth above a cap, or any change to `python.wasm`, is a finding for the build review,
     not a reason to accept.

     | metric | the confirmation's figure | cap |
     |---|---|---|
     | plain `-c pass` | +542,066 | ≤ +0.6 M |
     | plain `import numpy`, plain `import pandas`, and any check whose program only imports them and prints | +983,668; +835,650 | ≤ +1.5 M each |
     | every other plain check above 1 G fuel: the golden jobs (`compress` included, though it does not import numpy) and the rest | +0.004% to +0.05% (`pandas_csv` +2,765,223) | ≤ +0.2% of its accepted value each |
     | every other plain check (1 G fuel or less, no numpy) | about +0.54 M | ≤ +0.6 M each |
     | snapshot checks | +16,277 to +154,670 | ≤ +0.2 M each |
     | the zip's `bytes` (`test_stdlib_zip_is_bytecode_only_and_deflated`) | +20,532 | ≤ +25 KB |
     | the snapshot's `bytes` (`test_binary_is_a_core_wasm_module[snapshot]`) | +7,285 | ≤ +20 KB |
     | the plain binary's `bytes` | 0 | 0 |

   - **A heavy check above +2.5 M needs evidence.** For any plain check above 1 G fuel that grows
     by more than +2.5 M (inside its 0.2%), the account shows two things for that check:
     - that the stand-in's types were not built, by a copy of its program ending with
       `print('c_long' in vars(ctypes))` that prints `False`, as the confirmation did; or, if
       they were built, why;
     - that the rest is the collector's timing, as Decision 7 measured.
   - **The snapshot's growth is stated honestly.** It is about +0.14 M to +0.15 M on most
     snapshot checks. The account gives the measured split: the metadata members alone against
     the stand-in alone, as the review's `meta+snap` and `ctypes+snap` rows did. It says the cause is not
     profiled, and names the INFERRED one (finalization tearing down a moved heap, spec 021).
   - **The uncapped costs.** The account restates the first metadata lookup (about 0.36 G on the
     snapshot) and `import numpy.testing` (+136 M), which no existing check measures, and says
     spec 035 will re-measure them.
   - **What stays the same.** No golden output changes: no job reads metadata or uses `ctypes`.
     The judge holds no golden list of zip members (READ: no check compares member names or
     counts).
5. **The release.** A release dry run passes every job (the run of criterion 3).

## The owner's choices

None open here. Two choices the owner's decisions were silent on are decided above and recorded
as questions 57 and 58 in `../questions-for-the-owner.md`; nothing waits on them:
- landing before the zip's directory is read once;
- keeping "no ctypes" in the `-V` banner.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5), on darwin-arm64, uv 0.9.22, in the worktree
`wasi_python-033` on `spec/033-the-zip-carries-what-packages-need` (from `d98249b`); not yet
reviewed. Each claim is labelled. Scratch outputs are under
`/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/`
(`033-old/` today's set, `033-variants/` the split sets and probes, `033-mutant/` the mutant).

**What was built** (READ: the diff). As Design says, file by file:
- `scripts/make_stdlib_zip.py`: `wheel_members` keeps `<dist-info>/METADATA` and
  `<dist-info>/entry_points.txt`, bytes unchanged, and drops the rest of `.dist-info`, `.data`
  and any top-level `.egg-info`; `sdist_metadata(path)` and `--metadata`; `walk` skips
  `.egg-info` as well as `.dist-info`; `tree_members(tree)`, which `main` calls for each
  `--tree`, stops on a top-level `.dist-info` or `.egg-info` with Decision 3's line; the
  docstring.
- `scripts/steps/70_zip.sh`: two `--metadata` lines, three `--file` lines for the package.
- `recipes/ctypes_stand_in/__init__.py` (48 lines, comments rather than a docstring because every
  `import numpy` loads it): the constants, `WinError`, `__all__`, and a PEP 562 `__getattr__` and
  `__dir__`; the first lookup of a type name imports `._types` and stores every built name in the
  package's globals. `_types.py`: the metaclass (`t * n`, `n * t`), `_CData` (refusing
  `__new__`, the five classmethods, and a `__numpy_dtype__` that raises the `OSError`),
  `_SimpleCData` (a `__numpy_dtype__` returning `numpy.dtype(cls._numpy_code_)`), the simple
  types and CPython's aliases from `struct.calcsize`, the twins, `Structure`, `Union`,
  `POINTER`, `CFUNCTYPE`, `PYFUNCTYPE`, `sizeof`, the libraries, and the memory functions.
  `util.py`: `find_library` returns `None`. `recipes/ctypes_stub.py` is deleted.
- `tests/unit/test_build_scripts.py`: the four unit checks. `tests/checks/test_v1_3_data_stack.py`:
  the two guest checks, each on both binaries. `README.md` (the recipe paragraph, the platform
  paragraph, the zip's size 11.2 MB) and `CHANGELOG.md` (two 0.1.0a4 entries).

One refinement in a case the spec leaves open (for the review): when numpy is not in
`sys.modules`, a simple type's `__numpy_dtype__` raises `AttributeError` rather than `KeyError`,
so `hasattr` and `inspect.getmembers` on a stand-in type work before numpy is loaded. numpy is
always loaded when numpy asks.

**How the baseline was taken** (EXECUTED). The first full build in the worktree ran while I was
already editing: steps 00 to 60 passed (`python.wasm` `4befe9de64edc783`), and step 70 failed on
the deleted stub. Steps 00 to 60 read none of the changed files. I copied my three changed build
files aside, put `HEAD`'s versions back by hand (`git show HEAD:<path> >`), moved the untracked
package aside, and re-ran steps 70, 80 and 90: `cmp build/artifacts/SHA256SUMS
<main>/build/sets/4befe9de64edc783/SHA256SUMS` exits 0. That set is `$OLD`
(`python-stdlib.zip` `1add57e4…`, `python-snapshot.wasm` `c7302cfd…`, `MANIFEST` `e962887d…`).
Then my files went back and steps 70 to 90 ran with the change. Step 90 lists recipes from the
git index, so the new package must be staged before it runs (it stops on untracked recipe files).

**Criterion 1, seen failing first** (EXECUTED).
- The four unit checks, run in a `git archive HEAD` copy with the new test file: the wheel check
  fails (`wheel_members` yields `x.egg-info/PKG-INFO` and neither `METADATA` nor
  `entry_points.txt`); the `PKG-INFO` check fails on `no attribute 'sdist_metadata'`; the tree
  check on `no attribute 'tree_members'`; the stand-in check, with today's stub as the folder's
  `__init__.py`, on `no attribute 'c_long'` (and with no folder, `FileNotFoundError`).
- The guest checks on `$OLD`, both binaries: `test_packages_carry_their_metadata` exits 1 with
  `PackageNotFoundError: No package metadata was found for numpy`;
  `test_ctypes_stand_in_names_what_packages_import` reports 43 failures, the first two
  `import pandas.io.clipboard: ImportError: cannot import name 'c_size_t'` and
  `sympy's names: ImportError: cannot import name 'c_long'`; every dtype line fails with
  `AttributeError` (`no attribute 'c_double'`, `'c_long'`, `'c_int32'`), and
  `hasattr(np, 'ctypeslib')` is `False`.
- **The mutant** (the new zip with `ctypes/_types.pyc` recompiled without either
  `__numpy_dtype__`, plain binary): `np.dtype(ctypes.c_double)`, `np.dtype(ctypes.c_long)` and
  `np.asarray([1.5], dtype=ctypes.c_double).dtype` print `object object object` (the real
  stand-in: `float64 int32 float64`). The check's program then reports `dtype(c_double)`,
  `dtype(c_long)` and `dtype(c_int32 be)` false, `as_ctypes_type` and `from_dataframe` raising
  `NotImplementedError: Converting dtype('int32') to a ctypes type`, and `dtype(Structure)`
  raising nothing.
- With the change, all six pass (EXECUTED, the judge below).

**Criterion 2, the zip's names and bytes** (EXECUTED, the commands as written, from the worktree's
root, `$OLD` as above). The names diff is exactly `< ctypes.pyc`; `> ctypes/__init__.pyc`,
`> ctypes/_types.pyc`, `> ctypes/util.pyc`; `> numpy-2.5.2.dist-info/METADATA`,
`> pandas-3.0.6.dist-info/METADATA`, `> python_dateutil-2.9.0.post0.dist-info/METADATA`,
`> six-1.17.0.dist-info/METADATA`, `> tzdata-2026.5.dist-info/METADATA`; `unzip -Z1 | wc -l` is
1758. The shared-member comparison prints `1750 shared; 0 differ: []`. The five `cmp`s exit 0.
`cmp $OLD/python.wasm build/artifacts/python.wasm` exits 0. Then a full `scripts/build.sh` (all
11 steps, 5m29s) on the committed change (`e58f4f3`) gave the same `SHA256SUMS` again (`cmp`
exits 0). This was the worktree, which built every step from pins, not a clean clone; the lane's
clean-clone build is still to do.

**Criterion 3** (EXECUTED in part). The litter re-run: a `.DS_Store` in
`build/pandas-install/pandas/`, in numpy's installed package, and beside each `PKG-INFO`
(`build/numpy-2.5.2/`, `build/pandas-3.0.6/`), then steps 70 to 90: `SHA256SUMS` is the same
file (`cmp` exits 0); the litter was removed after. **Not done here: the release dry run**
(`gh workflow run release.yml --ref <branch>`, its `rebuild` and `same-bytes` jobs). That is the
lane's, on the reviewed commit, and its run number goes here.

**The new artifact set** (EXECUTED). Its `SHA256SUMS`, apart from the unchanged `LICENSES/` lines:

```
413f8494cbeb258bc0ea8a7d56e3f4929f5c6890b73bad2349905b99a4e71e0a  MANIFEST
98b03d8b711d2b1029d7a02c6c85b888e707fa7adff416c4357250c7f09454a2  python-snapshot.wasm
e9875f229c4decab5b15400a9243e47c92aa5c3eff4b377e0e491c11b0b3e540  python-stdlib.zip
4befe9de64edc783996ab006e6179b704a73a520b67431135df103db9db9625d  python.wasm
```

`python.wasm` unchanged (31,760,992 bytes, `4befe9de…`);
`python-snapshot.wasm` 65,505,782 bytes (`98b03d8b…`), −1,042; `python-stdlib.zip`
11,161,822 bytes (`e9875f22…`), +21,187; 1,100 pyc and 658 data files. `SHA256SUMS`
changes in the zip's, the snapshot's and `MANIFEST`'s lines only; `MANIFEST`'s `recipe` lines
change for the two scripts, and the stub's line is replaced by the three package lines.

**Criterion 4, the judge** (EXECUTED: `uv run pytest`, full tier, against the worktree's
`build/artifacts`, no `--accept`). The account, metric by metric (the judge's metrics in
`build/progress/latest.json` against `context/progress/accepted.json`):

| metric | the confirmation | measured | cap | |
|---|---|---|---|---|
| plain `-c pass`-sized checks (11, 217 M to 243 M) | +542,066 | +530,461 to +565,359 (`test_guest_runs_here[plain]` +543,042) | ≤ +0.6 M | ✓ |
| plain import-only: `numpy_and_pandas_are_builtin[plain]`, `nothing_is_a_shared_library`, `default_integer_width`, `longdouble_parses` | +983,668; +835,650 | +1,143,614; +1,391,847; +872,877; +1,255,668 | ≤ +1.5 M | ✓ |
| plain heavy (> 1 G): `numpy_csv`, `pandas_csv`, `numpy_random`, `compress`, `sqlite`, `npy_files_round_trip[plain]` | +0.004% to +0.05% | +0.0257%, +0.0440% (+2,499,648), +0.0025%, +0.0191%, +0.0213%, +0.0725% | ≤ +0.2% | ✓ |
| other plain ≤ 1 G: `guest_has_no_network`, `gzip_round_trips` | about +0.54 M | +533,029; +592,049 | ≤ +0.6 M | ✓ |
| other plain ≤ 1 G: `uncaught_errors_print_as_native[plain]` (670.7 M) | | **+624,482** | ≤ +0.6 M | **✗ over by 24,482** |
| snapshot checks (18 of 19) | +16,277 to +154,670 | −326,122 to +104,697 | ≤ +0.2 M | ✓ |
| snapshot: `stdlib_debugging_tools_import` (535.1 M) | | **+215,125** | ≤ +0.2 M | **✗ over by 15,125** |
| the zip's bytes | +20,532 | +21,187 | ≤ +25 KB | ✓ |
| the snapshot's bytes | +7,285 | −1,042 | ≤ +20 KB | ✓ |
| the plain binary's bytes | 0 | 0 | 0 | ✓ |

**Two caps are exceeded. Per criterion 4 these are findings for the build review, not reasons to
accept.** Neither program was measured by the confirmation. The evidence that both are the
collector's timing (EXECUTED, `033-variants/probe-1.tsv`, the judge's own driver):
- `import pdb, pydoc, doctest` on the snapshot: +215,074 (old 535,114,853, new 535,329,927). The
  same program after `import gc; gc.disable()`: **−85,342** (528,473,344 to 528,388,002).
- `1/0` on the plain binary: +624,397. After `gc.disable()`: **+460,162**, below the plain-start
  cost (+541,683 for `-c pass` in the same run).
- The types were not built in either: neither program names a C type.

They exceed their caps by 4.1% and 7.6%. The fix would be a cap that is relative for
programs past a few hundred M of fuel, as the confirmation did for the heavy plain ones; that is
the reviewer's and the owner's call, not the builder's.

**A heavy check above +2.5 M.** None: `pandas_csv` is the largest at +2,499,648. Its evidence
anyway (EXECUTED, `033-variants/jobs.tsv`): a copy ending with a print of whether `ctypes`' types
were built prints `False` on both sets, and that two-line tail alone moves the job's growth from
+2,498,560 to +3,109,847 (the collector's timing, as Decision 7 says). `numpy_csv` likewise:
`False`, +1,287,332 to +1,454,741.

**The snapshot's growth, split** (EXECUTED, variant sets made from `$OLD` and the new zip with
`make_stdlib_zip`'s own `member()`, snapshots with step 80's flags; the rewriter reproduces
`$OLD`'s zip and snapshot byte for byte). Snapshot `-c pass`: metadata alone +87,744, the
stand-in alone +111,981, both +67,223. On the plain binary: metadata alone +400,825, stand-in
alone +145,769, both +541,683; plain `import numpy` +308,504, +699,309, +1,038,845. The parts do
not add on the snapshot. The cause is not profiled. The INFERRED one is spec 021's: a moved heap
changes the work of finalization, about 97% of a snapshot `-c pass`. Snapshot bytes: metadata
alone +937, stand-in alone +3,468, both −1,042.

**The uncapped costs** (EXECUTED on the snapshot, old against new): `import importlib.metadata`
117,441,530 to 117,487,675 (about 35.5 M over `pass`, as before); the first `version("numpy")`
336,323,860 (`PackageNotFoundError`) to 478,501,836, **+142.2 M**, and 361.0 M over the import
alone; a second lookup (`pandas`) in the same process 23.5 M more (502,007,726);
`import numpy.testing` 463,864,591 to 600,088,569, **+136.2 M (+29.4%)**. No check measures
them. Spec 035's builder re-measures them with this change in.

**What stays the same** (EXECUTED: the judge). Every golden job's output is unchanged (each
`*_job_matches_native` passes). No check compares member names or counts.

**The scoreboard** (EXECUTED, run 2, after one fix): see the tail below. Run 1 found one lost
pass, `test_no_module_level_name_is_bound_twice`, on my unit file (`import importlib` and
`import importlib.util`); the plain `import importlib` was removed.

```
wasi_python v1: 196/200 pass · 0 gap · 4 blocked · 0 fail   (unit suite 583/590, 7 skipped)
  v1.1  artifact set        24/25  blocked 1
  v1.2  portable, sealed    40/41  blocked 1
  v1.3  data stack          20/21  blocked 1
  v1.4  embedding           73/73
  v1.5  rebuild from pins   18/18
  rules constitution rules  21/22  blocked 1
blocked by: oracle 1 · prior-art clones 1 · three systems 1 · wheel 1
ratchet vs f7b8df25de: lost 0 · absent 0 · unrun 0 · unrun locally 2 · gained 4 · grew 39 · judge changed: tests/checks/test_v1_3_data_stack.py, tests/unit/test_build_scripts.py
779 passed, 11 skipped
```

The four gained are the two new guest checks on both binaries; the 39 that grew are the table
above. Run 1 and run 2 agree within 34 fuel on six checks and exactly on the rest. `ruff check`
and `ruff format --check` are clean on `src/` and `tests/`. **For the lane:** the acceptance
needs `--accept-judge` (the two changed test files) and `--accept-growth`, which can cite the
table only after the build review answers the two over-cap findings. Then the release dry run
(criteria 3 and 5).
