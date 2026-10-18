# 033 — The zip carries what packages need

- **Status:** drafted 2026-10-17. It changes the build recipe and the artifact set, so it is
  reviewed once more before it is built (constitution §5.6). It is build-class (it touches
  `scripts/` and `recipes/`; §5.7).
- **Owner:** Clay Gendron
- **Kind:** the build recipe (`scripts/make_stdlib_zip.py`, `scripts/steps/70_zip.sh`), recipe
  files (`recipes/ctypes_stand_in/__init__.py` and `util.py` replace `recipes/ctypes_stub.py`),
  judge additions (`tests/checks/test_v1_3_data_stack.py`, `tests/unit/test_build_scripts.py`),
  `README.md`, `CHANGELOG.md`.
- **Depends on:** 003 (step 70 and the zip's rules), 012 (the same bytes from any host), 018
  (no litter in the zip), 020 (each source tree equals its pinned tarball plus the recorded
  patches), 004 and 009 (the licence notices in `LICENSES/`). All landed.
- **Research it stands on:** `../research/2026-10-17-what-else-the-default-profile-carries.md`,
  item 1 of "The order of specifications": finding 4a (step 70 drops `.dist-info`, so packages
  that read their own metadata fail: `df.to_markdown()` through tabulate, plotly, markdown's
  entry points; keeping `METADATA` and `entry_points.txt` fixed tabulate and markdown, EXECUTED),
  finding 4c (the `ctypes` stand-in is too thin for sympy and threadpoolctl, EXECUTED), finding 5
  (77,912 fuel per zip member on every plain start, EXECUTED). The evidence is beside the memo:
  `outputs/followup.tsv`, `outputs/guest/probe-sympy.stderr.txt`,
  `outputs/guest/probe-threadpoolctl.stderr.txt`. The owner's decisions 43 to 48
  (`../decisions.md`) and the roadmap's milestone 4 (`../roadmap.md`).

## The problem

Two things in today's zip stop pure-Python packages that would otherwise run.

**The zip has no package metadata.** Step 70 packs a wheel's code and drops its whole
`.dist-info` folder (`make_stdlib_zip.py`, `wheel_members`). numpy and pandas come in as trees
with no `.dist-info` at all: numpy from `meson install`, pandas from the sdist's folder. So in
the guest `importlib.metadata.version("numpy")` raises `PackageNotFoundError` (INFERRED from the
code: no `METADATA` member exists; the memo's probes ran this failure for tabulate, plotly and
altair, EXECUTED). Packages that ask for their own version or their entry points break:
tabulate reports version `unknown`, and pandas then refuses it, so `df.to_markdown()` fails
with `InvalidVersion: 'unknown'`; markdown's extensions by short name fail. numpy itself asks
at `import numpy.testing` (`numpy/testing/_private/utils.py:61`) and copes with the answer
"not installed".

**The `ctypes` stand-in has one function.** `recipes/ctypes_stub.py` defines `WinError` and
nothing else, because pandas imports `ctypes` unconditionally (`pandas/errors/__init__.py:8`)
and uses only that. Other importers need more names at import time, and fail:

| importer | what it needs at import | today |
|---|---|---|
| sympy 1.14.0 (`sympy/external/gmpy.py:3`) | `c_long`, `sizeof` | `ImportError: cannot import name 'c_long'` (EXECUTED by the memo) |
| threadpoolctl 3.7.0 (`threadpoolctl.py:56`) | `c_uint32` and the other fixed-width types, `Structure`, `c_char_p`, `c_void_p`, `DEFAULT_MODE`, `ctypes.util.find_library` | `AttributeError: … no attribute 'c_uint32'` (EXECUTED by the memo) |
| pandas 3.0.6 (`pandas/io/clipboard/__init__.py:51`), in today's zip | `c_size_t`, `c_wchar`, `c_wchar_p`, `get_errno`, `sizeof` | `ImportError` on `import pandas.io.clipboard` (READ: the stand-in defines none of them) |

sympy and threadpoolctl are tier A (approved, decision 43), and scikit-learn imports
threadpoolctl. pandas' clipboard module is in today's zip. Each would import with a stand-in
that names the C types and refuses every foreign call.

## Decisions

1. **A wheel keeps exactly two files of its `.dist-info`: `METADATA` and `entry_points.txt`.**
   `wheel_members` yields `<name>-<version>.dist-info/METADATA` and, when the wheel has one,
   `<name>-<version>.dist-info/entry_points.txt`, under the folder name the wheel gives them,
   with their bytes unchanged. Everything else in `.dist-info` stays out:
   - `RECORD`: it lists `.py` files and their hashes, and the zip holds `.pyc` files instead, so
     it would be false.
   - `WHEEL`, `INSTALLER`, `REQUESTED`, `direct_url.json`, `zip-safe`: facts about an install,
     which this zip is not.
   - `top_level.txt`: only `importlib.metadata.packages_distributions()` reads it, and every
     member costs every plain start (Decision 7). Left out.
   - Licence files (`LICENSE`, `licenses/…`): Decision 4.

   The `.data` folder stays out, as today. This is the memo's tested set (`followup.tsv`: 73
   members for 58 distributions).
2. **A package built from its sdist gets its `METADATA` from the sdist's `PKG-INFO`.** A new
   option, `make_stdlib_zip.py --metadata <PKG-INFO>`, packs that file, bytes unchanged, as
   `<name>-<version>.dist-info/METADATA`. The name and version come from the file's own `Name:`
   and `Version:` headers. The name is written as a wheel's folder name is: runs of `-`, `_` and
   `.` become one `_`, in lower case. A file without exactly one `Name:` and one `Version:`
   header before its first blank line stops the build with one line naming the file. Step 70
   passes `--metadata "$B/numpy-2.5.2/PKG-INFO"` and `--metadata "$B/pandas-3.0.6/PKG-INFO"`.
   - Why `PKG-INFO`: it is the project's own core metadata, in the same format as `METADATA`
     (numpy's is Metadata-Version 2.4, pandas' 2.1; READ). It sits in the pinned tarball, and
     spec 020's check proves the tree equals the tarball plus the recorded patches, none of which
     touches it. So it is pinned bytes, the same on every host.
   - **No `entry_points.txt` for these two.** Their entry points live in `pyproject.toml`
     (READ): numpy's are two console scripts and the `pkg_config`, `array_api` and
     `pyinstaller40` groups, none of which means anything in the guest; pandas' one is
     `pandas_plotting_backends: matplotlib`, and pandas loads its matplotlib backend by name
     before it looks at entry points (`pandas/plotting/_core.py:2177`, READ). Generating the
     file from `pyproject.toml` would be new code for nothing a guest uses.
3. **A tree never brings metadata of its own.** `walk` keeps skipping every `.dist-info` folder.
   A `--tree` that holds a `.dist-info` folder at its top now stops the build with one line ("pass
   it as a wheel, or its sdist's PKG-INFO with --metadata"), so a tree's metadata is never lost
   unnoticed. Today's two trees hold none (READ: `build/numpy-install`, `build/pandas-install`),
   so the build does not stop.
4. **Licence notices stay where they are.** The licence files inside `.dist-info` are not packed.
   Notices ship in the artifact set's `LICENSES/`, one file per component, built by
   `assemble_artifacts.py` from the pinned wheels and sources (specs 004 and 009). That is
   unchanged. `METADATA`'s `License:`, `License-Expression:` and `License-File:` headers name
   the licence; the files those headers name are not in the zip.
5. **The `ctypes` stand-in becomes a small package that names and sizes C types and refuses
   every foreign call.** `recipes/ctypes_stand_in/__init__.py` and `util.py` are packed as
   `ctypes/__init__.py` and `ctypes/util.py` (compiled to `.pyc`, as every module is);
   `recipes/ctypes_stub.py` is deleted. The recipe folder is not named `ctypes`, so nothing on a
   host can import it by accident. CPython's own `ctypes` stays out (`--skip ctypes`), since
   wasi-sdk has no libffi and the guest has no `_ctypes`. The stand-in holds:
   - **Simple types**, as classes: `c_bool`, `c_char`, `c_wchar`, `c_byte`, `c_ubyte`,
     `c_short`, `c_ushort`, `c_int`, `c_uint`, `c_long`, `c_ulong`, `c_longlong`, `c_ulonglong`,
     `c_size_t`, `c_ssize_t`, `c_int8` to `c_int64`, `c_uint8` to `c_uint64`, `c_float`,
     `c_double`, `c_longdouble`, `c_char_p`, `c_wchar_p`, `c_void_p`. Each has a `_type_` code.
   - **`sizeof`**, for a simple type or `POINTER(…)`. Sizes are wasm32's. Where `_type_` is a
     `struct` format code, the size is `struct.calcsize(_type_)`, computed in the guest at import
     (so `long` and `size_t` are 4). The three pointer types and every `POINTER(…)` take
     `struct.calcsize("P")`, also 4. `c_wchar` is 4 (WASI's `wchar_t` is 32-bit) and
     `c_longdouble` is 16 (wasm32's 128-bit `long double`, which step 40 already checks for
     numpy). The guest check compares every size with the guest's own `sysconfig` (Decision 8).
   - **Bases and factories:** `Structure` and `Union` can be subclassed, with `_fields_`, so a
     module that declares a C struct at import still imports. `POINTER(t)` returns one stand-in
     type per `t` (the same object each time); `CFUNCTYPE(restype, *argtypes)` and `PYFUNCTYPE`
     return a stand-in type.
   - **Libraries:** `CDLL`, `PyDLL`, `LibraryLoader`, `cdll`, `pydll`, and `DEFAULT_MODE`,
     `RTLD_GLOBAL`, `RTLD_LOCAL`.
   - **`WinError`**, as today.
   - **`ctypes.util.find_library(name)`** returns `None` for every name: the guest has no shared
     library to find.

   **The rule:** a name exists so that an import succeeds. Anything that would load a library,
   touch memory or make an instance raises `OSError("ctypes is unavailable on wasm32-wasi")`,
   today's message. That covers loading any library (`CDLL(None)` and `cdll.LoadLibrary(…)`
   included), instantiating any stand-in type, and `byref`, `pointer`, `cast`, `addressof`,
   `memmove`, `memset`, `string_at`, `create_string_buffer`, `create_unicode_buffer`,
   `get_errno`, `set_errno`. `OSError` is what CPython's `ctypes` raises when a library cannot
   be loaded, so code that copes with a missing library copes with this one. `sizeof` of a
   `Structure` or `Union` raises it too: the stand-in computes no layouts.

   **Why a stand-in that refuses, not more.** A stand-in that made instances (`c_int(3).value`)
   would mimic `ctypes` without its truncation or its memory. That would disguise the platform
   (§4.11). Naming and sizing types is true on wasm32; nothing more is claimed.
6. **threadpoolctl's own stand-in is deferred to the tier-A specification.** threadpoolctl is not
   in today's zip, and its only user in the approved profile is scikit-learn (tier B). With
   Decision 5, the real threadpoolctl imports. Its `threadpool_info()` then raises the
   stand-in's `OSError`, because it loads libc through `ctypes.CDLL(find_library("c"))`
   (`threadpoolctl.py`, `_get_libc`, READ in 3.6.0's source). The tier-A specification
   chooses between that and a small stand-in module of ours that reports no native thread pools,
   with scikit-learn's calls in view. The memo leans to the stand-in (INFERRED there). Adding a
   module named `threadpoolctl` now would put a package in the guest that nothing in it uses.
7. **What it costs, stated so growth can be told from regression.** Today's zip has 1,751
   members (EXECUTED: `unzip -Z1 build/artifacts/python-stdlib.zip | wc -l`). This change adds:
   - five `METADATA` members: numpy and pandas from `PKG-INFO`, python-dateutil, tzdata and six
     from their wheels. None of the three wheels has an `entry_points.txt` (READ: `unzip -Z1`);
   - one more for `ctypes`: `ctypes.pyc` becomes `ctypes/__init__.pyc` and `ctypes/util.pyc`.

   That makes **1,757 members, +6.** At 77,912 fuel per member (memo, finding 5), plain
   `-c pass` grows by about **0.47 M fuel** (6 × 77,912), about +0.19% of today's 241.5 M. The
   ratchet's tolerance is 0.01%, so every plain-binary check grows. Plain checks that import
   pandas also pay for the wider `ctypes` module, which `pandas.errors` imports. The five
   metadata files are 37,784 bytes before deflate (READ: `wc -c` gives numpy's `PKG-INFO` 6,635,
   pandas' 19,779, python-dateutil's `METADATA` 8,354, tzdata's 1,358, six's 1,658). So the zip
   grows by about 10 to 25 KB (INFERRED: text deflates about threefold, plus the larger `ctypes`
   bytecode). The snapshot holds the wider `ctypes` module, because pandas imports it while
   step 80 pre-imports the stack, and it holds a directory six entries longer. So the snapshot's
   bytes grow a little, and its checks may move as spec 021's did (INFERRED). `python.wasm` does
   not change: step 60 is untouched.

   With tier A the rule adds about one or two members per distribution: the memo measured 73
   for 58 distributions, +6.0 M fuel on a plain start (`followup.tsv`, EXECUTED). Cutting the
   per-member cost is the next specification's job, "the zip's directory is read once"
   (decision 44; its research is under way in
   `../research/2026-10-17-the-zips-directory-is-read-once/`). This one does not touch zipimport
   or `zipfile`.

   **A metadata lookup's own cost.** `importlib.metadata` reads a zip through `zipfile.Path`,
   which parses the whole central directory in Python. That costs about 116,000 fuel per member
   (memo, finding 4e), so about 0.2 G for the first lookup in a process with 1,757 members
   (INFERRED). Later lookups in the same process reuse it: CPython 3.15 caches it per path and
   modification time (`importlib/metadata/__init__.py`, `FastPath.__new__`'s `lru_cache` and
   `lookup`'s `method_cache`, READ). Programs that never ask for metadata pay nothing. Step 80's
   pre-import asks for none (READ: `import numpy` and `import pandas` reach `importlib.metadata`
   only through `numpy.testing` and the plotting-backend loader, which they do not import), so no
   cached lookup is frozen into the snapshot.
8. **The checks** (Design). Two guest checks go in v1.3, each on both binaries:
   - `test_packages_carry_their_metadata`: `importlib.metadata.version` gives MANIFEST's version
     for numpy and pandas, equal to `numpy.__version__` and `pandas.__version__`. The guest's
     `importlib.metadata.distributions()` is exactly python-dateutil, tzdata, six, numpy and
     pandas, each at its MANIFEST version. A later specification that adds a package adds it to
     this set. `importlib.metadata.files("numpy")` is `None`, because `RECORD` is not kept, and
     the check says so. Seen failing first: today `version("numpy")` raises
     `PackageNotFoundError`.
   - `test_ctypes_stand_in_names_what_packages_import`: `import pandas.io.clipboard` succeeds
     (seen failing first: today it raises `ImportError` on `c_size_t`). sympy's import-time
     names (`from ctypes import c_long, sizeof`) and threadpoolctl's (the fixed-width types,
     `c_char_p`, `c_void_p`, `Structure` subclassed with `_fields_`, `DEFAULT_MODE`, and
     `from ctypes.util import find_library`) resolve. These are written by name in the check, not
     copied from either package. `sizeof` of each simple type equals the guest's
     `sysconfig.get_config_var("SIZEOF_…")` (`SIZEOF__BOOL`, `SIZEOF_SHORT`, `SIZEOF_INT`,
     `SIZEOF_LONG`, `SIZEOF_LONG_LONG`, `SIZEOF_SIZE_T`, `SIZEOF_VOID_P` for the three pointer
     types and `POINTER(c_int)`, `SIZEOF_WCHAR_T`, `SIZEOF_FLOAT`, `SIZEOF_DOUBLE`,
     `SIZEOF_LONG_DOUBLE`; the build's `_sysconfigdata` has each, READ), and the fixed-width
     types' sizes are their widths. `find_library("c")` is `None`. `CDLL(None)`, `c_int(1)`,
     an instance of the `Structure` subclass and `byref` each raise `OSError` with Decision 5's
     message. `ctypes.WinError()` still raises `OSError`. `import ctypes.wintypes` raises
     `ImportError`. Seen failing first: today `c_long` is missing.

   The real sympy, threadpoolctl and tabulate imports, and `df.to_markdown()`, are checked by
   the tier-A specification, which puts those packages in the zip.

   Unit checks in `tests/unit/test_build_scripts.py` cover the zip builder and the stand-in on
   the host (Design).
9. **Ordering with other build-class work.** This specification and spec 023 (matplotlib M1)
   both change step 70, so they never build at once (§5.7). Whichever lands second applies this
   one's rule to the other's packages. Every Python distribution in the zip gets its `METADATA`:
   - a pinned wheel through `--wheel`, automatically;
   - a package built from its sdist (matplotlib, kiwisolver, Pillow) through `--metadata` with
     that sdist's `PKG-INFO`.

   That distribution then joins the set in `test_packages_carry_their_metadata`.
10. **What the change does to the artifact set.** The zip changes: six new or moved members,
    everything else byte for byte. The snapshot changes with it. `python.wasm` does not change.
    `MANIFEST`'s `recipe` lines change for `scripts/make_stdlib_zip.py` and
    `scripts/steps/70_zip.sh`. `recipes/ctypes_stub.py`'s line is replaced by the two
    `recipes/ctypes_stand_in/` lines. `SHA256SUMS` changes in the zip's, the snapshot's and
    `MANIFEST`'s lines. The `-V` banner keeps "no ctypes": no foreign function can be called,
    which is what it says. The README explains what the stand-in does (Design).

## Intent

A package that asks for its own version, its entry points or a C type's size gets a true answer
from the zip. A package that tries to call C gets the `OSError` it would get on a machine without
the library.

## Design

| file | change |
|---|---|
| `scripts/make_stdlib_zip.py` | `wheel_members` keeps `METADATA` and `entry_points.txt` (Decision 1); `--metadata` and a function `sdist_metadata(path) -> (bytes, member name)` (Decision 2); a `--tree` with a top-level `.dist-info` stops the build (Decision 3); the docstring's usage line |
| `scripts/steps/70_zip.sh` | two `--metadata` lines; the two `--file` lines for `ctypes/__init__.py` and `ctypes/util.py` replace the `ctypes.py` one |
| `recipes/ctypes_stand_in/__init__.py`, `recipes/ctypes_stand_in/util.py` | new (Decision 5); the simple types made in one loop from a table of names and codes, so the module stays short and cheap to import; `__init__` does not import `util` |
| `recipes/ctypes_stub.py` | deleted |
| `tests/checks/test_v1_3_data_stack.py` | `test_packages_carry_their_metadata[plain, snapshot]`, `test_ctypes_stand_in_names_what_packages_import[plain, snapshot]` (Decision 8) |
| `tests/unit/test_build_scripts.py` | the unit checks below |
| `README.md` | the recipe paragraph (now "one-function stand-ins for `ctypes` and `mmap`") describes the `ctypes` package; the platform paragraph gains two sentences: `importlib.metadata` gives each package's name, version and entry points, and `files()` gives `None`; `import ctypes` works and sizes wasm32's C types, but loads no library and calls nothing (`OSError`) |
| `CHANGELOG.md` | under 0.1.0a4: the zip keeps package metadata; the wider `ctypes` stand-in |

Unit checks, each seen failing first against today's scripts or stub:

- `test_the_zip_keeps_a_wheels_metadata_and_entry_points`: a temporary wheel with a module,
  a `.data/` file, and a `.dist-info/` holding `METADATA`, `entry_points.txt`, `RECORD`,
  `WHEEL`, `INSTALLER`, `REQUESTED`, `direct_url.json`, `top_level.txt`, `zip-safe` and
  `licenses/LICENSE`. `wheel_members` yields the module, `METADATA` and `entry_points.txt`, with
  their bytes unchanged, and nothing else. Today it yields the module only.
- `test_an_sdists_pkg_info_becomes_metadata`: a `PKG-INFO` with `Name: Foo.Bar-baz` and
  `Version: 1.0` becomes `foo_bar_baz-1.0.dist-info/METADATA` with its bytes unchanged. One
  without `Name:`, one without `Version:`, and one with two `Version:` headers each stop with
  one line naming the file. Today the function does not exist.
- `test_a_tree_with_dist_info_stops_the_zip`: `main` with a `--tree` holding `x-1.0.dist-info/`
  stops with Decision 3's line. Today it packs the tree and drops the folder.
- `test_the_ctypes_stand_in_names_and_refuses`: the recipe is loaded on the host under a
  private module name (never as `ctypes`). Every Decision 5 name exists. `CDLL(None)`,
  `CDLL("libc.so")`, `cdll.LoadLibrary("x")`, an instance of each simple type, a `Structure`
  subclass's instance and each memory function raise `OSError` with the message. `POINTER(c_int)
  is POINTER(c_int)`. `CFUNCTYPE(c_int, c_char_p)` is a type. `sizeof(c_wchar) == 4` and
  `sizeof(c_longdouble) == 16`. `util.find_library("c") is None`. The sizes taken from
  `struct` are checked in the guest, not here, because the host's `long` is not wasm32's.
  Today's stub fails at `c_long`.

## Scope

In: the above. Out:

- **Real sympy, threadpoolctl, tabulate and markdown in the zip,** with their judge jobs: the
  tier-A specification, after "the zip's directory is read once" (decisions 44 and 45).
- **threadpoolctl's stand-in:** the tier-A specification (Decision 6).
- **`numpy.ctypeslib` and `ndarray.ctypes`.** They need `ctypes` types that numpy can turn
  into dtypes, which means `_ctypes`. They fail before this change and after it (READ:
  `numpy/ctypeslib/_ctypeslib.py` builds its scalar map at import).
- **`df.to_clipboard()` and `pd.read_clipboard()`.** Their module now imports. Whether they
  then raise pandas' "could not find a copy/paste mechanism" error, as expected, is not checked.
  A clipboard means nothing in a sandbox.
- **Array types (`c_char * n`), struct layouts and `sizeof` of a `Structure`:** no importer
  named here needs them.
- **`top_level.txt`, `RECORD` and `importlib.metadata.packages_distributions()`** (Decision 1).
- **Entry points for numpy and pandas** (Decision 2).
- **Any change to zipimport, `zipfile` or the per-member or per-read cost:** "the zip's
  directory is read once", the next specification.

## Acceptance criteria

1. The four unit checks and the two guest checks exist, and each was seen failing first as
   Decision 8 and Design say. Today's set fails the guest checks with `PackageNotFoundError` for
   numpy and with `ImportError` on `c_size_t` and `c_long`.
2. A full build from pins in a clean clone gives a `python.wasm` byte for byte the same as
   today's. The zip has today's 1,751 names minus `ctypes.pyc`, plus `ctypes/__init__.pyc`,
   `ctypes/util.pyc` and the five `METADATA` members (1,757). Every member it shares with
   today's zip is byte for byte the same. The five `METADATA` members equal their source files
   byte for byte (each wheel's `METADATA`, and numpy's and pandas' `PKG-INFO`).
3. The zip is the same bytes from every host: the release dry run's rebuild jobs (spec 012,
   Decision 7) pass. Steps 70 to 90, re-run with a `.DS_Store` in each input tree (spec 018's
   criterion), give the same bytes again.
4. `uv run pytest` is green with `--accept "<reason>" --accept-judge "<the new checks>"
   --accept-growth "<the build's measured account>"`; lost 0. The account names what grew, by
   how much and why:
   - the zip's `bytes` metric (`test_stdlib_zip_is_bytecode_only_and_deflated`): expected +10 to
     +25 KB;
   - the snapshot's `bytes` metric (`test_binary_is_a_core_wasm_module[snapshot]`): a small
     growth;
   - every plain-binary fuel metric: about +0.47 M on short programs (Decision 7). Plain checks
     that import pandas grow by that much plus the wider `ctypes` module's import;
   - snapshot fuel metrics: small moves, explained as spec 021 explained its own.

   The plain binary's `bytes` metric does not move. No golden output changes: no job reads
   metadata or calls `ctypes`. The judge holds no golden list of zip members (READ: no check
   compares member names or counts). A plain `-c pass` growth above 0.6 M, or any change to
   `python.wasm`, is a finding for the build review, not a reason to accept.
5. A release dry run passes every job.

## Questions for the owner

None open here. Two choices the owner's decisions were silent on (landing before the zip's
directory is read once; keeping "no ctypes" in the `-V` banner) are decided above and recorded as
questions 57 and 58 in `../questions-for-the-owner.md`; nothing waits on them.

## Landing notes

Not built.
