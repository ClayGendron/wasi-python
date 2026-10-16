# What matplotlib needs

- **Status:** research (desk study), 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: about 90 minutes;
  stopped at about 75, with the gaps listed under "Where it stopped".
- **Feeds:** the matplotlib specification (constitution §2, "Beyond
  v1", first in order). It adds two reasons to
  `2026-10-16-the-cpython-3-15-and-wasi-sdk-33-line.md`, which it
  depends on.
- **Stands on:** the spike memo's finding 10
  (`2026-10-16-the-spike-that-proved-the-build.md`), which estimated
  matplotlib at two to four weeks on the 3.15 / SDK-33 line.

## The question

What would it take to compile matplotlib into the static `python.wasm`
(`wasm32-wasip1`, CPython, numpy and pandas as builtins), under the
constitution's rules: zero upstream patches, every input pinned and
hashed, two imports only, static builtins through the inittab? The
target is headless: `import matplotlib; matplotlib.use("Agg");
plt.savefig("/out/x.png")`, and the same to SVG.

## Method

- **PyPI metadata** for matplotlib, contourpy, kiwisolver, pillow,
  fonttools, cycler, packaging, pyparsing, python-dateutil, numpy,
  pybind11, meson-python, cppy, setuptools, setuptools-scm and pkgconf
  (`curl https://pypi.org/pypi/<name>/json`; EXECUTED). Versions and
  hashes below come from it.
- **Sources read outside the repository.** Five sdists (matplotlib,
  contourpy, kiwisolver, pillow, pybind11) and the five tarballs
  matplotlib's meson wraps name (FreeType, HarfBuzz, libraqm,
  SheenBidi, qhull) were downloaded into the session scratchpad, not
  into `downloads/` or `build/`. Each was checked against its PyPI
  digest or its wrap's `source_hash` (`shasum -a 256 -c`: all ten
  `OK`; EXECUTED). They were unpacked there and read with `grep`;
  nothing was built.
- **Prior art (READ):**
  - `pyodide-recipes` @ 01bd0af: matplotlib 3.10.8 and its five
    patches; the contourpy, kiwisolver and Pillow recipes.
  - `wasi-sdk` @ 2b65040: `SetjmpLongjmp.md`, `CppExceptions.md`,
    `cmake/wasi-sdk-sysroot.cmake`.
  - The same cmake file at the `wasi-sdk-24` and `wasi-sdk-33` tags,
    through `raw.githubusercontent.com`.
  - `wasmtime/crates/wizer` @ 2d9c19b.
- **Local files (READ):** the wasi-sdk 24 sysroot under
  `build/tools/`, and `mesonbuild/wrap/wrap.py` inside the pinned
  `downloads/meson-1.12.1-py3-none-any.whl`.
- **One guest probe (EXECUTED).** It ran on the spec-003 artifacts in
  `build/artifacts/` (CPython 3.14.8, SDK 24) through
  `wasi_python.run(["-c", …], root=<scratch dir>)`. The run used the
  snapshot, an empty environment, and exited 0. Its results are cited
  as "the probe".

## Findings

### 1. matplotlib 3.11.2 builds with meson, pybind11 and five native libraries

- **The release (EXECUTED).** The latest release is 3.11.2, published
  2026-09-11. Its sdist is `matplotlib-3.11.2.tar.gz`, sha256
  `cec596316640f2b394b8f0daa0ea61a8eae82d017b620b9f202befb972a59ea4`.
  PyPI has `cp315` wheels for it, so upstream builds it for Python
  3.15.
- **The build system (READ, `pyproject.toml`, `meson.build`).**
  - The backend is `mesonpy`. The build needs `pybind11>=2.13.2` and
    `setuptools_scm>=7,<10`.
  - `meson.build` takes the project version from `python3 -m
    setuptools_scm` at configure time.
  - It defaults to `b_lto=true`, `cpp_std=c++17` and
    `auto_features=disabled`.
  - It finds pybind11 with `dependency('pybind11')`.

**The compiled modules (READ, `src/meson.build`).** They are all
C++17 and all use pybind11:

| module (install path) | sources | needs |
|---|---|---|
| `matplotlib.ft2font` | `ft2font.cpp`, `ft2font_wrapper.cpp` | FreeType, libraqm (which needs HarfBuzz and SheenBidi), Agg headers |
| `matplotlib.backends._backend_agg` | `_backend_agg.cpp`, `_backend_agg_wrapper.cpp` | Agg |
| `matplotlib._image` | `_image_wrapper.cpp`, `py_converters.cpp` | Agg |
| `matplotlib._path` | `_path_wrapper.cpp` | Agg |
| `matplotlib._c_internal_utils` | `_c_internal_utils.cpp` | nothing on WASI; its `dlopen` code is under `#ifdef __linux__` |
| `matplotlib._qhull` | `_qhull_wrapper.cpp` | qhull (`libqhull_r`) |
| `matplotlib._tri` | `tri/_tri.cpp`, `tri/_tri_wrapper.cpp` | nothing |
| `matplotlib.backends._tkagg` | `_tkagg.cpp` | nothing at build time; it `dlopen`s Tcl/Tk at run time, so it is useless here |

**The native libraries (READ, `extern/meson.build`,
`subprojects/*.wrap`).**

- **Agg** is always vendored (`extern/agg24-svn`, a static library).
- **FreeType 2.14.3** comes from a wrap. Its options are
  `png=disabled` and `zlib=internal`, and its HarfBuzz is static.
- **HarfBuzz 14.1.0** comes from a wrap. It is C++.
- **libraqm 0.10.5** comes from a wrap. It is C.
- **SheenBidi 3.0.0** comes from a wrap. It is C.
- **qhull 8.0.2** comes from a wrap. It has no meson build of its own;
  matplotlib supplies one through `patch_directory`.
- **libpng is not used.** FreeType is built with `png=disabled`, and
  matplotlib writes PNG through Pillow (finding 5).

**New since 3.10: libraqm is unconditional (READ).** `src/ft2font.h:31`
includes `<raqm.h>` with no `#if`. `ft2font.cpp:305-410` calls
`raqm_*` for every text layout. So matplotlib 3.11 needs HarfBuzz,
libraqm and SheenBidi on top of FreeType. Pyodide's recipe pins 3.10.8,
which predates this.

### 2. Four runtime dependencies are compiled, five are pure Python

| package | latest (EXECUTED, PyPI) | kind | build system (READ) |
|---|---|---|---|
| numpy | 2.5.4 (we pin 2.5.2) | C/C++ | meson (already built) |
| contourpy | 1.4.0 | C++, pybind11, one module `_contourpy` | meson, `werror=true` default |
| kiwisolver | 1.5.1 | C++, plain C-API with `cppy` (not pybind11), one module `_cext` | setuptools + cppy |
| pillow | 13.0.0 (uploaded 2026-10-16 22:18 UTC, hours old) | C; `_imaging` plus optional modules | setuptools with a custom backend; imports `pybind11.setup_helpers` only for parallel compiling |
| fonttools | 4.67.0 | pure (`py3-none-any` wheel exists) | — |
| cycler | 0.12.1 | pure | — |
| packaging | 26.3 | pure | — |
| pyparsing | 3.3.3 | pure | — |
| python-dateutil | 2.9.0.post0 (already pinned, with six) | pure | — |

pybind11's latest is 3.1.0 (EXECUTED). It is header-only, a build tool.

**Pillow (READ, `setup.py`).**

- Its required features are `{"jpeg", "zlib"}` (line 327).
- A disable flag drops a feature from the required set (lines
  404-408). So a zlib-only build is allowed.
- It also has a `disable-platform-guessing` option (line 364), which
  stops it adding the host's include and library directories.
- `setjmp` appears only in the JPEG files (`src/libImaging/Jpeg*.{c,h}`).
  So a zlib-only Pillow needs no setjmp.

**Pyodide builds contourpy and kiwisolver with no patches and no
flags (READ).** It builds Pillow with `platform-guessing=disable` and
switches for each feature.

### 3. matplotlib downloads five tarballs itself; both ways to pin them work, one breaks no rule

**What it downloads (READ, the wrap files).** By default, `meson setup`
downloads the five wrap tarballs (finding 1) into
`subprojects/packagecache/`. It then unpacks each into
`subprojects/<name>/`, inside matplotlib's own tree. Then it applies
matplotlib's own diff files to those trees:

| diff file | what it does |
|---|---|
| `freetype-2.14.1-static-harfbuzz.patch` | lets FreeType use the static HarfBuzz |
| `freetype-2.14.1-wasm-visibility.patch` | drops hidden visibility, under Emscripten only |
| `0001-Don-t-force-any-diagnostics-to-be-errors.patch` (HarfBuzz) | adds `-DHB_NO_PRAGMA_GCC_DIAGNOSTIC_ERROR` and one ignored warning |
| `libraqm-0.10.2-bundle-freetype.patch` | drops `method: 'pkg-config'` |
| `qhull-143.patch` | printf format attributes, warnings only |

**Route A: the subprojects, offline (READ, `wrap.py`).** This keeps
matplotlib's default build.

- Meson reads `MESON_PACKAGE_CACHE_DIR` (line 380).
- It uses a cached file once `check_hash` passes against the wrap's
  `source_hash` (lines 951-956).
- So the five tarballs pinned in `downloads/SHA256SUMS`, plus
  `MESON_PACKAGE_CACHE_DIR=downloads/` and `--wrap-mode=nodownload`,
  give an offline build.
- **But it breaks two rules.** It writes inside matplotlib's unpacked
  tree (`subprojects/<name>/`; spec 003 Decision 4). It also modifies
  the FreeType, HarfBuzz, libraqm and qhull trees with diff files
  (constitution §4.1: no file in any source tree is modified). They
  are matplotlib's diffs, not ours. Whether that counts is the owner's
  call.

**Route B: the system libraries (READ, `meson.options`,
`extern/meson.build`).** This route breaks no rule.

- Configure with `-Dsystem-freetype=true -Dsystem-libraqm=true
  -Dsystem-qhull=true`.
- Build each library as its own step, from its pinned tarball,
  unpatched, outside its tree, the way step 30 builds zlib.
- **FreeType** has a meson build. Use `harfbuzz=disabled`. The
  static-HarfBuzz diff is not needed, because FreeType's HarfBuzz
  support is optional.
- **HarfBuzz** has a meson build. The only effect of matplotlib's
  HarfBuzz diff that matters is a define, `-DHB_NO_PRAGMA_GCC_DIAGNOSTIC_ERROR`
  (`src/hb.hh:63`). A cross-file argument can pass it.
- **SheenBidi and libraqm** each have a `meson.build`.
- **qhull** has only CMake and a Makefile. A recipe compiles
  `src/libqhull_r/*.c` into `libqhull_r.a`. The system-qhull path
  needs only `cc.check_header('libqhull_r/qhull_ra.h')` and
  `cc.find_library('qhull_r')`, so an include flag and a `-L` in the
  cross file are enough.
- **The cost: a pinned pkg-config.** `dependency('freetype2')` and
  `dependency('raqm')` need pkg-config, and our cross files set
  `pkg-config = 'false'`. The PyPI `pkgconf` 3.0.7.post0 wheel is a
  candidate. The libraries' installs write their `.pc` files.
  `dependency('pybind11')` can use the same tool, or `pybind11-config`
  named in the cross file.

**INFERRED: Route B is the one that keeps §4.1 whole without a
ruling.** It is also the shape the project already has: one step per C
library.

### 4. C++ exceptions and setjmp make the SDK-33 line a hard prerequisite, for three separate reasons

**(a) Throwing is the ordinary error path (READ).**

- **pybind11 3.1.0** converts every Python error crossing C++ into a
  thrown `error_already_set`. 115 `throw error_already_set` /
  `throw cast_error` sites are in `include/pybind11/*.h`.
- Its overload dispatcher throws and catches `reference_cast_error`
  while choosing an overload. It is thrown at `cast.h:119` and
  `detail/type_caster_base.h:1691`, and caught at `pybind11.h:1237`,
  `1268`, `1282` and `1289`.
- **matplotlib** throws on user errors.
  - `_backend_agg.cpp:33`: "dpi must be positive".
  - `_image_wrapper.cpp:84-150`: wrong array shapes.
  - `ft2font.cpp`: 24 `throw` sites, for FreeType errors and layout
    failures.
  - `mplutils.h:66-94` and `py_converters.h:67-136`:
    `py::value_error`.
  - Its FreeType read callback catches `error_already_set`
    (`ft2font_wrapper.cpp:470`, `:487`).
- **kiwisolver** throws solver errors (`kiwi/solverimpl.h:86-608`) and
  catches them into Python exceptions (`py/src/solver.cpp:58-200`).
- On SDK 24, the spike's `cxa_stubs.c` turns every throw into
  `abort()`. So a bad argument, or a font error, would kill the guest.

**(b) pybind11 3.x does not compile on SDK 24 at all (READ).**

- `include/pybind11/detail/internals.h:24-25` includes `<mutex>` and
  `<thread>` with no guard.
- SDK 24's wasip1 libc++ is configured `_LIBCPP_HAS_NO_THREADS`
  (`build/tools/wasi-sdk-24.0-arm64-macos/share/wasi-sysroot/include/wasm32-wasip1/c++/v1/__config_site:16`).
- Its `<thread>` then fails with `#error "<thread> is not supported…"`
  (`…/c++/v1/thread:91-92`).
- wasi-sdk 24 built libc++ with `-DLIBCXX_ENABLE_THREADS:BOOL=${threads}`,
  that is, off for wasip1 (tag `wasi-sdk-24`, `cmake/wasi-sdk-sysroot.cmake:235`).
- wasi-sdk 33 builds it with `ON` for every target
  (tag `wasi-sdk-33`, same file, line 309).
- contourpy's `threaded.cpp:5` also includes `<thread>`.

**(c) FreeType and qhull use setjmp/longjmp (READ).**

- wasi-libc's `setjmp.h` stops with `#error` unless
  `__wasm_exception_handling__` is defined (the SDK-24 sysroot,
  `include/wasm32-wasip1/setjmp.h`). FreeType's `ftstdlib.h:168-173`
  maps `ft_setjmp` to `setjmp`.
- FreeType calls `ft_setjmp` while validating each TrueType cmap
  (`src/sfnt/ttcmap.c:3843`), so it runs on every font load.
- qhull calls `setjmp` in `qh_new_qhull` (`libqhull_r/user_r.c:151`)
  and `longjmp`s on every qhull error.
- Pyodide uses Emscripten's `freetype-legacysjlj` port for this reason
  (`matplotlib/meta.yaml`).
- `SetjmpLongjmp.md` prescribes `-mllvm -wasm-enable-sjlj -lsetjmp
  -mllvm -wasm-use-legacy-eh=false`. It also says that only clang 20
  and later (wasi-sdk 26 and later) can emit the standard
  exception-handling instructions. SDK 24 is clang 18.
- **So C++ exceptions and setjmp ride on the same wasm feature, and
  SDK 33 has both.** Use `-fwasm-exceptions -mllvm
  -wasm-use-legacy-eh=false` and `-lunwind` for C++ (`CppExceptions.md`).
  Use the sjlj flags for FreeType and qhull.

**Two consequences (INFERRED).**

- **Every embedder needs exception handling.** `python.wasm` will
  carry the instructions of the standard exception-handling proposal,
  so every embedder's engine must support it. The spike ran a
  throw/catch probe under the wasmtime 49 CLI and wasmtime-py's
  default engine (EXECUTED in the spike). Other engines are untested.
  The README must say so.
- **Wizer must take those instructions.** Wasmtime's `wizer` crate
  validates with `WasmFeatures::all()` (`lib.rs:273`) and accepts tag
  exports (`parse.rs:121`). Whether the pinned wizer 11.0.3 snapshots
  such a module has not been run. That is an experiment for the 3.15
  line.

### 5. The smallest headless set: five matplotlib modules, kiwisolver, a zlib-only Pillow, four pure packages

**`import matplotlib` imports more than its name suggests (READ).**

- `__init__.py:246-265`, `_check_versions()`, imports `ft2font`,
  `cycler`, `dateutil`, `kiwisolver`, `numpy` and `pyparsing`.
- Line 157 imports `packaging.version`.
- Line 163 imports `matplotlib.colors`, which imports `PIL.Image`
  (`colors.py:53-54`). So Pillow's `_imaging` is needed by `import
  matplotlib` itself.
- `text.py` imports `textpath`, which imports `dviread`, which imports
  `fontTools.agl` at top level (`dviread.py:32`). So fonttools is
  needed by any figure with text.
- `axes/_axes.py:18` imports `matplotlib.dates`, which needs dateutil.

**Three things load lazily (READ).**

- `contourpy` loads only inside `ContourSet` (`contour.py:1333`).
- `_qhull` and `_tri` load only inside `tri/_triangulation.py`.
- `_tkagg` loads only with the Tk backend.

**How PNG and SVG are written (READ).**

- **PNG:** `backend_agg.py:480-488` draws with Agg, then calls
  `mpl.image.imsave`, which calls `PIL.Image.save` (`image.py:12-13`,
  `1601-1705`). So PNG is Agg plus Pillow's zlib encoder. matplotlib
  has no libpng of its own.
- **SVG:** `backend_svg.py` is pure Python, but it imports `PIL.Image`
  (line 14). With the default `svg.fonttype: path`, its text goes
  through `textpath` to `ft2font`, so it needs the fonts too.

**The smallest set for `matplotlib.use("Agg")` with `savefig` to PNG
and SVG (INFERRED from the READ chain above):**

- **compiled:**
  - matplotlib's `ft2font`, `_path`, `_image`, `_c_internal_utils` and
    `backends._backend_agg`, with FreeType, HarfBuzz, libraqm,
    SheenBidi and Agg;
  - kiwisolver `_cext`;
  - Pillow `_imaging` with zlib only. Its `_imagingmath` and
    `_imagingmorph` are cheap optional extras.
- **pure Python:** cycler, pyparsing, packaging, fonttools. numpy,
  python-dateutil and six are already in.
- **outside the smallest set:** contourpy, `_qhull`/`_tri` (and
  qhull), `_tkagg`, and Pillow's `_imagingft`, `_imagingcms`,
  `_webp`, `_avif` and `_imagingtk`.
  - matplotlib's configure step still requires a qhull, so the library
    is built in either case.
  - Linking `_qhull` and `_tri` costs little and makes `tricontour`
    work. Leaving out contourpy breaks `contour`/`contourf` with an
    `ImportError`. The full set is the honest product. The smallest
    set is the order to build in.

**The default backend (READ).** `-DrcParams-backend=Agg` is a meson
option (`meson.options`). It writes `backend: Agg` into the generated
`matplotlibrc` (`lib/matplotlib/mpl-data/meson.build`). Then pyplot
never probes the GUI backends.

### 6. Traps

**6.1 matplotlib cannot live in the stdlib zip (EXECUTED, READ).**

- **The probe:** `open()` of a module path inside the zip raised
  `NotADirectoryError: [Errno 54]`, and `os.path.isfile` on it
  returned `False`.
- **The data path follows the package.** `get_data_path()` is
  `Path(__file__).with_name("mpl-data")` (`__init__.py:638-640`).
- **The import reads files with plain `open()`.** `import matplotlib`
  reads `mpl-data/matplotlibrc` that way (`__init__.py:992`, and
  `_open_file_or_url` at lines 878-880).
- **Fonts are opened the same way.** FreeType never opens a font
  itself. `FT2Font` opens a path with Python's `io.open` and feeds
  FreeType through a stream callback (`ft2font_wrapper.cpp:448-475`,
  `568-573`). `findfont` also checks `os.path.isfile`
  (`font_manager.py:1699`).
- **So the limit is Python's `open`, not FreeType.** Every path under
  the zip fails.
- **The way out without a patch:** the matplotlib package is a real
  directory on a `sys.path` entry. `/usr/local/lib/python3.14` is
  already on `sys.path` (spike memo, finding 1).
- **That changes the artifact set and the root layout.** It touches
  constitution §4.6, spec 003 Decisions 7 and 9, and the runner's
  `_place_stdlib`. So it needs an owner decision and a pre-build
  review.
- **Size (EXECUTED, `du -sk`).** `mpl-data` is 9,916 KB. 8,872 KB of
  that is fonts: 42 files in `fonts/ttf`, plus AFM files.

**6.2 Threads (EXECUTED, READ).**

- The probe's `threading.Timer(...).start()` raised `RuntimeError:
  can't start new thread`. `import threading` and
  `threading.get_ident()` worked.
- matplotlib 3.11.2 already catches that error
  (`font_manager.py:1248-1253`). So Pyodide's patch 0001 is no longer
  needed.
- contourpy's `threaded` algorithm spawns `std::thread`
  (`threaded.cpp:252-256`). It would fail at run time only when chosen.
  matplotlib's default algorithm is `mpl2014` (INFERRED).
- HarfBuzz's meson asks for `dependency('threads')` (`meson.build:353`).
  meson may then add `-pthread`, which on wasip1 pulls in shared-memory
  features. The `wasi-cc` wrapper should drop it (INFERRED; untested).

**6.3 The config and cache directory (EXECUTED, READ).**

- **What matplotlib does on `wasi`.** `sys.platform` is `wasi`, so
  `_get_config_or_cache_dir` takes the `Path.home() / ".matplotlib"`
  branch (`__init__.py:561-565`).
- **`Path.home()` fails.** The probe's `Path.home()` raised
  `RuntimeError: Could not determine home directory.`
- **The fallback.** matplotlib then calls `tempfile.mkdtemp`
  (`__init__.py:586-599`). In the probe, that made `/matplotlib-…`
  in the root. matplotlib also warns on stderr and registers an
  `atexit` `rmtree`.
- **The cost.** Every fresh instance would then rebuild the font list:
  it opens all of `mpl-data/fonts` through `FT2Font`, which costs
  fuel.
- **No patch is needed.** Set `MPLCONFIGDIR`.
  - **For the snapshot**, `wizer.initialize` sets `MPLCONFIGDIR`
    before it pre-imports `matplotlib.pyplot`. The `FontManager` then
    lives in snapshot memory.
    - The font files must sit at the same paths at run time.
    - A snapshot taken without `MPLCONFIGDIR` would carry an
      `atexit` `rmtree` of a directory that exists only in the Wizer
      root. `Py_FinalizeEx` would then print an ignored exception
      (INFERRED).
  - **For the plain reactor**, a fontlist JSON can be generated once
    and shipped in the config directory. The JSON stores font paths
    relative to the data path (`font_manager.py:1134`, `1152`), so it
    is portable. This replaces Pyodide's patch 0002.

**6.4 `/dev/null` (READ, INFERRED).** `_qhull` opens `MPL_DEVNULL` with
`fopen` when it hides qhull's errors. It throws "Could not open
devnull" if that fails (`_qhull_wrapper.cpp:179-182`). The path is the
cross file's `devnull` property (`src/meson.build:9-13`). A guest root
need not have `/dev/null`. The specification must pick a path.

**6.5 Static-link clashes (READ, INFERRED).**

- **FreeType's internal zlib cannot clash with ours.** It is compiled
  file-local (`src/gzip/ftgzip.c:74`: "prevent zlib functions from
  being visible outside their object files").
- **Agg is linked once.** It is one static library shared by three
  modules, and step 60's `sort -u` of the `.deps` lists links it once.
- **pybind11 code must come from one pin.** matplotlib and contourpy
  both instantiate pybind11 templates. In one static link the linker
  keeps one copy of each inline function. So both must build against
  the same pinned pybind11, with the same flags.
- **Module init names.** They are `PyInit_ft2font`, `PyInit__path`,
  `PyInit__image`, `PyInit__tri`, `PyInit__qhull`,
  `PyInit__backend_agg`, `PyInit__c_internal_utils`,
  `PyInit__contourpy`, `PyInit__cext` and `PyInit__imaging`. None
  matched a numpy or pandas module name I know of (INFERRED). Step
  60's duplicate-symbol detector is the check.

**6.6 Inittab names (READ, INFERRED).**

- matplotlib declares every extension in `src/meson.build`, with an
  install `subdir`. So the archives land in `<build>/src/`, not under
  the package path. contourpy does the same.
- `scripts/gen_inittab.py` takes dotted names from build-directory
  paths. It would need the install paths, for example from `meson
  introspect --installed`.

**6.7 Build flags that are options, not patches (READ).**

| flag | why it is needed |
|---|---|
| `-Db_lto=false` | `CppExceptions.md` lists exceptions with LTO as broken (wasi-sdk #629) |
| `-Dwerror=false` for contourpy | contourpy turns on `werror` by default |
| a `devnull` cross property | `_qhull` needs a path it can open (6.4) |
| the macOS backend | needs nothing: it builds only on Darwin hosts |

`b_lto`, `werror` and the `devnull` property are all meson-level.

**6.8 The version and the install (READ).**

- **The version.** `python3 -m setuptools_scm` runs at configure time,
  so the host Python needs setuptools_scm below 10 (9.2.2 is the
  latest 9.x).
- **The install.** `matplotlibrc` is generated
  (`tools/generate_matplotlibrc.py`). So the package must come from
  `meson install` with tag filters, as numpy's does (step 40), and not
  from a copy of the sdist tree, as pandas' does.

**6.9 Two packages build with setuptools (READ, INFERRED).**

- kiwisolver and Pillow have no meson build. The `wasi-cc` archive
  trick still applies: it only reacts to `-shared -o X.so`.
- **The driver is the question.** `setup.py build_ext` would run
  under `scripts/python-wasi-cross` (the target sysconfig), with `CC`,
  `LDSHARED` and `AR` set to the wrapper tools.
- **For Pillow, the flags are** `--disable-jpeg`, `--disable-tiff` and
  the other feature switches, plus `--disable-platform-guessing`.
- **The alternative** is a recipe `meson.build` that lists their
  sources. That copies their source lists, and it would rot.

**6.10 Size (EXECUTED; native only, not wasm).** The manylinux
x86_64 cp314 wheels hold these unstripped `.so` files:

| package | `.so` bytes | notes |
|---|---|---|
| matplotlib | 9,177,704 | `ft2font` with FreeType, HarfBuzz and raqm is 3,315,768 of it; `_tkagg` is 609,048 |
| Pillow `_imaging` | 3,486,065 | |
| contourpy | 993,568 | |
| kiwisolver | 5,735,032 | likely debug info |

- **INFERRED:** `python.wasm` grows by roughly 6 to 12 MB.
- The tree adds about 10 MB on disk.
- The zip grows by a few MB of deflated `.pyc`. matplotlib's
  `lib/matplotlib` is 47,984 KB in the sdist: 31,808 KB of tests,
  9,916 KB of `mpl-data`, and about 6 MB of Python source (EXECUTED,
  `du -sk`).
- All three must be measured at build time.

**6.11 Licences: an owner approval list (READ; constitution
§4.12).**

| component | licence |
|---|---|
| matplotlib | its PSF-style agreement |
| Agg | BSD-style |
| FreeType | FTL, or GPLv2 at the user's choice |
| HarfBuzz | MIT ("Old MIT") |
| libraqm | MIT |
| SheenBidi | Apache-2.0 |
| qhull | the Qhull licence |
| Pillow | MIT-CMU |
| contourpy | BSD-3-Clause |
| kiwisolver | BSD-3-Clause |
| fonttools | MIT |
| cycler | BSD-3-Clause |
| pyparsing | MIT |
| packaging | Apache-2.0 or BSD-2-Clause |

The fonts carry their own licences: DejaVu (Bitstream Vera plus public
domain), STIX (OFL), BaKoMa/Computer Modern, and Last Resort (OFL).
matplotlib's `meson.build` lists 16 licence files.

### 7. Pyodide's five patches, re-judged for 3.11.2 on WASI

| patch | what it works around | here |
|---|---|---|
| 0001 Disable timer | `threading.Timer.start()` fails without threads | Not needed: 3.11.2 catches the `RuntimeError` (6.2) |
| 0002 Hardcode font cache path | no writable `get_cachedir()`; a shipped `fontlist.json` | Not needed: `MPLCONFIGDIR`, the snapshot, or a shipped cache (6.3) |
| 0003 Pyodide webagg backend | showing figures in a browser | Out of scope (headless) |
| 0004 Fix 32-bit casting | `unsigned int` to `py::ssize_t` (32-bit) narrowing in a braced initialiser | Upstream in 3.11.2 (`_backend_agg_wrapper.cpp:257-262`). If it comes back, `-Wno-c++11-narrowing` is a flag-level answer (INFERRED) |
| 0005 Use system FreeType | a "function signature mismatch" in the bundled FreeType on Emscripten; the switch to Emscripten's sjlj FreeType port | Route B builds FreeType ourselves, unpatched, with `-Dsystem-freetype=true`. A signature mismatch would show as wasm-ld's warning, which step 60 already fails on |

So all five drop away. None of them becomes a patch here (READ for
each patch; the verdicts are INFERRED).

## What it decides

1. **The 3.15 + SDK 33 line comes first, and is no longer optional for
   matplotlib.** Three independent facts each block SDK 24:
   - throws on ordinary paths;
   - pybind11 3.x's `<thread>` include;
   - FreeType's and qhull's setjmp.

   The placeholder memo gains one more experiment: a setjmp/longjmp
   probe built with the sjlj flags, run under wasmtime and through
   Wizer.
2. **Two owner decisions come before a specification.**
   - **The root layout.** It gains a matplotlib directory beside the
     zip (6.1), so the artifact set and the embedder's contract
     change. The alternative is that matplotlib waits.
   - **The licence list (6.11).**
3. **Route B for the native libraries (finding 3).** Each is its own
   step from a pinned tarball, unpatched, with a pinned pkg-config.
   Route A would need a ruling on matplotlib's own wrap diffs.
4. **The proposed order of work,** each step with a counted check
   first:
   1. Land the 3.15 + SDK 33 line (its memo). Add the sjlj and Wizer
      probe.
   2. The C libraries as steps after zlib: FreeType, SheenBidi,
      HarfBuzz, libraqm and qhull. Check: each archive links into a
      hello-world wasm, and a FreeType program loads DejaVu Sans and
      renders one glyph.
   3. Pillow, zlib only. Check: `PIL.Image.new("RGB", (4, 4)).save("/out/x.png")`
      round-trips.
   4. kiwisolver, then contourpy. Check: a forced
      `UnsatisfiableConstraint` arrives as a Python exception, not a
      trap.
   5. matplotlib: meson with the `system-*` options,
      `-DrcParams-backend=Agg`, `-Db_lto=false` and the `devnull`
      property; then `meson install`.
   6. The link and the layout. Inittab names from the install paths;
      the pure packages in the zip; the matplotlib tree placed by the
      runner; `MPLCONFIGDIR` in `wizer.initialize`, with `pyplot`
      pre-imported.
   7. Golden jobs: a line plot saved to PNG and SVG. Compare the
      decoded PNG pixels and the SVG text with native matplotlib at
      the same pinned FreeType. A bad `dpi` must raise `ValueError`,
      not trap.
5. **The estimate stands at two to four weeks of agent work after the
   3.15 line lands (INFERRED).** HarfBuzz, libraqm and SheenBidi add
   to the spike's estimate. Upstream has absorbed Pyodide's two real
   patches, which takes some away.

### The new pins

Every hash is EXECUTED: read from PyPI's JSON, and for the ten
tarballs also checked against the downloaded bytes. Versions are the
latest as of 2026-10-16. The specification picks the final set.

```
# sources built into python.wasm
cec596316640f2b394b8f0daa0ea61a8eae82d017b620b9f202befb972a59ea4  matplotlib-3.11.2.tar.gz
20156f5a1ac4f8ce02656e39a61e82164a3d359796dc8026f75b062783d500e1  contourpy-1.4.0.tar.gz
f1303ef2eec81262a4b708c3e858afe58d7c75ad91c1c05266eda7673369859a  kiwisolver-1.5.1.tar.gz
cdcd1ba258178f7356d74170c9a81ba4eab6a5d55748bc402a5a2a6fe6be3510  pillow-13.0.0.tar.gz
36bc4f1cc413335368ee656c42afca65c5a3987e8768cc28cf11ba775e785a5f  freetype-2.14.3.tar.xz
ee0eb3a1da2c5a28147f12dff55f6c7d60aeeeb29ac7ef334eabe84c8476c105  harfbuzz-14.1.0.tar.xz
7f3dd21b4b3bd28a36f2c911d31d91a9d69341697713923ef1aac65d56ebcafd  libraqm-0.10.5.tar.gz
86c56014034739ba39a24c23eb00323b0bf6f737354f665786015fca842af786  sheenbidi-3.0.0.tar.gz
8774e9a12c70b0180b95d6b0b563c5aa4bea8d5960c15e18ae3b6d2521d64f8b  qhull-8.0.2.tgz
# pure Python, into the zip
85cef7cff222d8644161529808465972e51340599459b8ac3ccbac5a854e0d30  cycler-0.12.1-py3-none-any.whl
ece8c00a69cf01b45d0b1dedabb469c90d8caf996d4fda40f147627a122849a4  pyparsing-3.3.3-py3-none-any.whl
d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c  packaging-26.3-py3-none-any.whl
4304f03ed7f4ba000a8dcc941ad854bfa52e2f3b6112b8f099b6f431cf98e701  fonttools-4.67.0-py3-none-any.whl
# build tools (host side)
b8488090f8acffbcb6b5d6a85571a6827a0a2981ffb75e5a0b27b87c4a6b7dd0  pybind11-3.1.0-py3-none-any.whl
30e8f84d2ab1ba7cb0e653429b179395d0c33775d54807fc5f1dd6671801aef7  setuptools_scm-9.2.2-py3-none-any.whl
51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670  setuptools-84.0.0-py3-none-any.whl
7ca132b6ef6187384738804bd3a453d4eab7e3274df6dcd35e5d92aae3404717  cppy-1.3.1-py3-none-any.whl
47cbf6889d84297b9a4e1741ae016daa4e198f3ec8bab7ce74554cc50b77cce4  pkgconf-3.0.7.post0-py3-none-macosx_11_0_arm64.whl
```

- **The sdist and tarball URLs** are in the PyPI JSON and in
  matplotlib's wrap files.
- **wasi-sdk 33** is already a research pin (`85c997a2…`). It becomes
  a build pin with the 3.15 line.
- **That is 18 new lines.** They are 9 sources, 4 pure wheels and 5
  build tools, plus each package's licence files.
- **Linux CI needs more.** It needs the Linux pkgconf wheel.
  setuptools_scm 9.2.2's own dependencies were not resolved here.
- **Pillow 13.0.0 was hours old** when it was read. The specification
  may prefer the last 12.x release.

## Where it stopped

These were not done in the box. Each is an experiment, not a guess:

- No wasm sizes. No build of any library.
- Not run: whether wizer 11.0.3 snapshots a module with exception
  handling.
- Not checked: whether meson's threads dependency really emits
  `-pthread` for HarfBuzz under our cross file.
- Not checked: which optional FreeType modules (`gxvalid`, `otvalid`)
  the default module list compiles.
- Not tried: whether Pillow's `setup.py build_ext --disable-*` runs
  under the cross Python.
- setuptools_scm 9.2.2's own dependency pins were not resolved.

The probe's scratch root and the downloaded sources stay in the
session scratchpad. Nothing in the repository changed except this
memo.

## One line

matplotlib 3.11 can be built with no patches. It first needs the SDK-33
line (for C++ exceptions, pybind11's `<thread>` and FreeType's setjmp),
five C libraries built as their own pinned steps, a zlib-only Pillow,
kiwisolver, and an owner decision to put the matplotlib package and its
fonts on the guest filesystem, outside the zip.
