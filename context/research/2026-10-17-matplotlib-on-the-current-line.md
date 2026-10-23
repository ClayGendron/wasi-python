# matplotlib on the current line

- **Status:** research (desk study plus a scratch build), 2026-10-17
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: about three hours, kept. Where it stopped is listed at the end.
- **Feeds:** the matplotlib specification (constitution §2, "Beyond v1", first in order now that spec 017 has landed).
- **Refreshes:** `2026-10-16-what-matplotlib-needs.md` (called "the old memo" here). It stands on `2026-10-16-where-package-data-lives.md`, `2026-10-16-cpp-exceptions-and-wasi-hosts.md`, spec 017 (typed grants) and spec 020 (carried patches).
- **Evidence:** everything ran in the session scratchpad, `…/scratchpad/mpl-research/` (`dl/` for downloads, one folder each; `work/` for builds; `scripts/` for the probes; `e0/` to `e3/` for guest runs). The probe scripts and the two patches are copied beside this memo, in `2026-10-17-matplotlib-on-the-current-line/` (`scripts/`, `patches/`); the builds, downloads and binaries are not (artifacts never live in git). Nothing else in the repository changed. The main tree's toolchain was used read-only: wasi-sdk 33, the pinned meson 1.12.1, the host Python 3.15.0, the CPython 3.15 objects of step 60, and wasmtime 49.0.3.

## The question

The old memo was a desk study on the 3.14 line. The line is now CPython 3.15.0, wasi-sdk 33 and numpy 2.5.2, typed grants have landed, and §4.1 now allows carried patches. So:

1. Which of the old memo's findings still hold? Are its versions still the right ones today?
2. With typed grants, how does matplotlib's data (`mpl-data`: fonts, `matplotlibrc`, styles) reach the guest? What does the font cache need?
3. Does anything now need a carried patch?
4. How much do `python.wasm`, the snapshot and the zip grow? Should the snapshot pre-import matplotlib?
5. What is the smallest useful first milestone?
6. What are the ordered steps and the new pins? Which questions for the owner remain?

## Method

- **Versions (EXECUTED).** PyPI's JSON for every package, GitHub's release API for HarfBuzz, libraqm, SheenBidi, qhull and zlib, and the FreeType and libpng download listings, all on 2026-10-17.
- **Downloads (EXECUTED).** Each candidate went into its own folder under `dl/` and was checked with `shasum -a 256 -c` against the old memo's hash, the PyPI digest or matplotlib's wrap `source_hash`: all `OK`. One mismatch was found and explained (finding 1).
- **A scratch build (EXECUTED).** All five C libraries, matplotlib, contourpy, kiwisolver and a zlib-only Pillow were compiled for `wasm32-wasip1` with SDK 33. They were linked with step 60's own reactor link command (read from `build/link/reactor-commands.txt`, run in the CPython cross-build folder with the output sent to scratch). A scratch zip and two scratch snapshots were made from them.
- **Guest runs (EXECUTED).** Through the judge's reference embedder, `tests/harness/guest.py`, imported read-only from the main tree. It allows any guest path, so it could grant the data under `/usr/local/lib`, which `wasi_python.run` refuses to an embedder (spec 017, Decision 4).
- **Native reference (EXECUTED).** A scratch venv (`uv venv`, CPython 3.14.2) with the same pins from PyPI wheels. Nothing was installed outside the scratchpad.
- **Upstream (READ).** matplotlib's `main` branch and pull request #30291 through GitHub's API.

Fuel is wasmtime's count of guest instructions. It is a count, so it is evidence. The few wall-clock figures are benchmark facts from one M-series Mac.

## Findings

### 1. The versions: keep the old memo's set; Pillow 13.0.0 is now fine

| component | old memo | latest today (EXECUTED) | cp315 wheels on PyPI | pick |
|---|---|---|---|---|
| matplotlib | 3.11.2 | 3.11.2 (2026-09-11) | yes | 3.11.2 |
| contourpy | 1.4.0 | 1.4.0 | yes | 1.4.0 |
| kiwisolver | 1.5.1 | 1.5.1 | yes | 1.5.1 |
| Pillow | 13.0.0 | 13.0.0 (2026-10-16); 12.3.0 before it | yes, both | 13.0.0 |
| fonttools | 4.67.0 | 4.67.0 | yes (pure wheel too) | 4.67.0 pure |
| cycler, pyparsing, packaging | 0.12.1, 3.3.3, 26.3 | same | pure | same |
| pybind11 | 3.1.0 | 3.1.0 | pure | 3.1.0 |
| FreeType | 2.14.3 | **2.15.0** (2026-10-12) | – | **2.14.3** |
| HarfBuzz | 14.1.0 | **14.6.0** (2026-10-05) | – | **14.1.0** |
| libraqm | 0.10.5 | **0.11.0** (2026-07-23) | – | **0.10.5** |
| SheenBidi | 3.0.0 | 3.0.0 | – | 3.0.0 |
| qhull | 8.0.2 (2020.2) | 8.0.2; only 8.1 alphas since | – | 8.0.2 |
| libpng | not used | 1.6.59 | – | not needed |

- **Why not the newest C libraries (INFERRED, with an EXECUTED reason).** matplotlib 3.11.2 pins FreeType 2.14.3 in its wrap, and the wrap says it "must match `LOCAL_FREETYPE_VERSION`". Its PyPI wheels are built with exactly the wrap versions. With the same versions, our wasm output is pixel-identical to the native wheel's (finding 6). A newer FreeType or HarfBuzz could move glyph pixels and lose that oracle.
- **Pillow (READ, the 13.0.0 release notes).** 13.0.0 drops Python 3.10 and says "Python 3.15 is now officially supported". Its removals (`Image._show`, `ImageCms` product fields and others) do not touch matplotlib's path. It ran clean in every guest run below. 12.3.0 is the fallback.
- **The qhull URL matters (EXECUTED).** qhull.org's `qhull-2020-src-8.0.2.tgz` has sha256 `b5c2d7eb…`, not the wrap's `8774e9a1…`. The pin is GitHub's `https://github.com/qhull/qhull/archive/v8.0.2/qhull-8.0.2.tar.gz`, as matplotlib's wrap names it.
- **numpy 2.5.4 is out (EXECUTED); the line pins 2.5.2.** matplotlib needs `numpy>=1.25`, so this does not block it.
- **An aside (EXECUTED, not matplotlib's).** zlib 1.3.2 was released 2026-02-17; the line pins 1.3.1. Whether 1.3.2 carries a security fix (§5.5) was not checked.

### 2. What still holds from the old memo, and what changed

| old memo | today |
|---|---|
| 1. meson, pybind11, five native libraries | **Holds (EXECUTED).** Route B built every library unpatched, from its tarball, with flags only. |
| 2. four compiled packages, five pure ones | **Holds (EXECUTED).** kiwisolver and Pillow compile directly from their source lists; no setuptools run is needed. |
| 3. Route B needs pkg-config | **Holds (EXECUTED).** The scratch build used Homebrew's `pkg-config`; the specification pins `pkgconf` 3.0.7.post0, one wheel per build host. |
| 4. SDK 33 is required (exceptions, `<thread>`, setjmp) | **Resolved (EXECUTED).** The line is on SDK 33. pybind11 3.1.0 compiles. A C++ throw reaches Python (kiwisolver's `UnsatisfiableConstraint`, `dpi must be positive` as `ValueError`). FreeType's cmap validator and qhull's `qh_errexit` `longjmp` and return. Wizer snapshots the module. |
| 4. Wizer and EH untested | **Resolved (EXECUTED).** `wasmtime wizer` with step 80's flags snapshotted the module carrying both C++ and setjmp exception code. |
| 4. HarfBuzz's `-pthread` untested | **Confirmed a trap (EXECUTED).** meson adds `-pthread` 56 times. The objects then carry `+atomics` and 1,865 atomic instructions, a new host requirement. A `wasi-cc` that drops `-pthread` removes both, and the shaping output is unchanged. |
| 5. the smallest headless set | **Holds (EXECUTED).** `import matplotlib` loads `PIL._imaging`, `ft2font` and kiwisolver; PNG goes through Pillow. |
| 6.1 matplotlib cannot read data from the zip | **Holds; solved by a grant (EXECUTED, finding 3).** |
| 6.2 threads | **Holds (EXECUTED).** `threading.Timer(...).start()` raises `RuntimeError`, and matplotlib carries on. |
| 6.3 the config and cache folder | **Holds (EXECUTED).** Without `MPLCONFIGDIR` and `HOME`, matplotlib warns and makes `/matplotlib-xxxxxxxx` in the root. See finding 4. |
| 6.4 `/dev/null` | **Worse than thought (EXECUTED).** Every Delaunay triangulation raised `RuntimeError: Could not open devnull`. No path is writable on every call, so the cross-file property alone cannot fix it. A carried patch fixes it (finding 5). |
| 6.5 static-link clashes | **Holds (EXECUTED): none.** No `PyInit_` name clashes with the 130 already linked; the link printed no warnings. **But a new trap was found:** a static constructor that calls Python (finding 5). |
| 6.6 inittab names | **Holds (EXECUTED).** The archives sit in `build/src/`. Also, `_qhull`'s `.deps` names `-lqhull_r`, which step 60's `grep '\.a$'` would drop. |
| 6.7 build flags | **Holds (EXECUTED).** `-Db_lto=false`; `-Dwerror=false` for contourpy; the `devnull` property. |
| 6.8 the version and the install | **Changed (EXECUTED).** A six-line stand-in for `python3 -m setuptools_scm` (it prints `PKG-INFO`'s version) replaces pinning setuptools_scm and its dependencies. `meson install` with the `runtime` tag fails on a macOS host (`install_name_tool` on the archives); `--tags python-runtime,data` installs exactly the package and `mpl-data` without them. |
| 6.9 Pillow and kiwisolver drivers | **Resolved (EXECUTED).** Pillow: 76 C files read from `setup.py`'s `_IMAGING` and `_LIB_IMAGING` tuples (by `ast`, not by running it), with `-DHAVE_LIBZ`. kiwisolver: its 7 `.cpp` files and cppy's headers. |
| 7. Pyodide's five patches drop away | **Holds.** But two patches of our own are now needed (finding 5). |
| "no patches" | **Does not hold (EXECUTED).** See finding 5. |

Three more facts the old memo did not have (EXECUTED):

- **contourpy asks the target Python for meson-python's version** at configure time (`lib/contourpy/util/meson.build:29`). A `METADATA`-only `meson_python-0.22.1.dist-info` on the cross Python's path answers it.
- **contourpy writes builder paths into `contourpy/util/_build_config.py`** (`build_dir`, `source_dir`, `python_path`). That file goes into the zip, so it must be rewritten like numpy's `__config__.py` (spec 012, Decision 5).
- **The link gains one WASI import, `fd_renumber`** (qhull's `freopen`). It is a preview1 call, so §4.4 holds: the imports are still WASI plus `host::call`.

### 3. The data: a runtime grant at the path matplotlib computes; the code stays in the zip

**What matplotlib looks for (READ, `lib/matplotlib/__init__.py`).**

- `get_data_path()` is `Path(__file__).with_name("mpl-data")` (lines 638-640). Nothing else. `MATPLOTLIBDATA` appears only in a docstring (line 660); no code reads it.
- With matplotlib's `.pyc` in the zip, that path is `/usr/local/lib/python315.zip/matplotlib/mpl-data`.
- So a grant at `/usr/local/share/matplotlib` would never be found. It would work only if matplotlib's code left the zip for a folder on `sys.path`, and spec 006 Decision 4 keeps `sys.path` to the zip alone, for safety.

**A grant nested under the zip's own grant works (EXECUTED, `e0`).** On today's artifacts, a read-only preopen at `/usr/local/lib/python315.zip/matplotlib/mpl-data`, beside the stdlib's read-only grant at `/usr/local/lib`, gave on both binaries and in both preopen orders:

```
decimal from /usr/local/lib/python315.zip/_pydecimal.pyc     imports still come from the zip
rc ## REAL rc True                                           open() and isfile() reach the grant
listdir ['fonts', 'matplotlibrc'] True
font bytes 756072
write w PermissionError 63 ; write a PermissionError 63      the grant is read-only
parent NotADirectoryError 54                                 matplotlib/ inside the zip is not a folder
```

The snapshot honours it in any order, because `wizer.initialize` already calls `__wasilibc_reset_preopens()` (`recipes/reactor_main.c:206`, READ).

**Who grants it.**

- **The runner, as its own grant (recommended).** Spec 017 refuses an embedder's grant at or under `/usr/local/lib` (Decision 4, READ). So the runner adds it, as it adds the zip: read-only, on every call, from a private per-process copy that it checks.
- **Other embedders** add one line to the README's contract: for matplotlib, preopen the data folder read-only at that guest path. An embedder that never imports matplotlib can leave it out.
- **Where the bytes travel (recommended, INFERRED).** Keep `matplotlib/mpl-data/` inside the stdlib zip as plain members. The runner extracts that one folder once per process into a private folder beside its zip copy, and grants it. Then:
  - the artifact set keeps its shape (§4.6 unchanged);
  - the snapshot is already paired with the zip by hash (`x-snapshot-zip`), and its frozen font list then pairs with the same hash;
  - the zip grows by 4,834,287 bytes (204 files, 9,647,776 bytes raw, deflated at level 9; EXECUTED). Fonts barely compress.

  The alternative is a separate `mpl-data` archive in the artifact set. It changes §4.6 and needs its own pairing line. The specification decides.

**The font cache and the config folder.**

- **The order (READ, `__init__.py:528-603`).** `MPLCONFIGDIR`, then on `wasi` `Path.home() / ".matplotlib"`, then `tempfile.mkdtemp()` with a warning and an `atexit` `rmtree`. If no folder is writable, `import matplotlib` raises `OSError`.
- **On the snapshot, with pyplot pre-imported (EXECUTED).** The choice is frozen at build time. The runs printed `cachedir /tmp/matplotlib` and an empty stderr, with no `HOME` at all. The font list (`fontManager`, 40 fonts) and `rcParams` live in snapshot memory, so no run reads or writes the cache. `HOME` does not matter.
- **On the plain reactor (EXECUTED).** Each fresh `HOME` rebuilds the font list. That costs 1,990,636,000 fuel more than a warm cache (8,305,875,937 against 6,315,239,947 for `import matplotlib.pyplot`). Without `MPLCONFIGDIR` or `HOME`, it warns and makes `/matplotlib-…` in the root.
- **With `root=False` and no writable `/tmp` (INFERRED from the code, not run):** on the plain reactor `import matplotlib` raises `OSError`. On the pre-imported snapshot it does not matter.
- **A shared, writable cache is trusted by later runs (READ, `font_manager.py:1834-1849`).** The JSON lists font paths. That is the same exposure spec 001 names for a shared root. The pre-imported snapshot never reads it.
- **One behaviour differs on the snapshot (INFERRED).** `./matplotlibrc` and `$MATPLOTLIBRC` are read at import, so on the snapshot they are never read. `matplotlib.rc_file()` still works. The README should say so.

### 4. Size and start-up: measured

**Sizes (EXECUTED, `wc -c`; stripped as step 60 strips).**

| artifact | today | with matplotlib | growth |
|---|---|---|---|
| `python.wasm` | 31,760,997 (a scratch relink; the artifact is 31,760,992) | 38,008,426 | +6,247,429 (+19.7%) |
| stdlib zip | 11,140,578 | 17,677,855 (no `mpl-data`) | +6,537,277 (+58.7%) |
| zip with `mpl-data` inside | – | about 22.5 MB | about +11.4 MB (INFERRED: the sum) |
| snapshot, same pre-imports as today | 65,506,914 | 71,992,243 | +6,485,329 (+9.9%) |
| snapshot, `matplotlib.pyplot` pre-imported | – | 89,475,378 | +23,968,464 (+36.6%) |
| snapshot's initial memory | 56 MiB | 57 MiB / **74 MiB** pre-imported | +18 MiB |

- **Where `python.wasm`'s bytes go (EXECUTED, the link map's symbol sizes; 4,299,244 bytes in all).** HarfBuzz 1,018,924; FreeType 629,517; `ft2font` 607,864; contourpy 388,785; Pillow `_imaging` 323,677; `_backend_agg` 309,332; qhull 302,293; `_image` 196,532; `_path` 172,863; `_tri` 109,420; kiwisolver 104,984; SheenBidi 58,390; the rest under 25 KB each. libc++ and libc++abi grow by about 336 KB (iostream, locale). The rest of the growth is tables and the name section (INFERRED).
- **Where the zip's bytes go (EXECUTED).** matplotlib 2,576,784; fontTools 2,279,428; PIL 686,540; mpl_toolkits 245,022; pyparsing 243,431; packaging 226,027; contourpy 61,732.
- `_tkagg` was left out of the link. It would add an unusable module.

**Start-up (EXECUTED, fuel; `e3` and `e5`).**

| binary | `pass` | `import matplotlib.pyplot` | the milestone plot program |
|---|---|---|---|
| today's snapshot | 81,967,339 | – | – |
| matplotlib snapshot, no pre-import | 83,599,182 | 6,651,911,204 cold cache; 4,657,901,954 warm | 5,808,970,290 (warm) |
| matplotlib snapshot, pyplot pre-imported | 107,017,873 | 107,059,469 | 1,254,675,963 |
| plain matplotlib reactor | 294,035,774 | 8,305,875,937 cold; 6,315,239,947 warm | 7,476,213,418 (warm) |

- **The +23.4 M fuel of a bare call is all teardown (EXECUTED).** With `os._exit(0)` in place of a normal exit, both snapshots cost about 2.67 M (2,672,838 and 2,677,635). So `Py_FinalizeEx` tearing down the pre-imported modules is the whole difference.
- **The split (EXECUTED, warm cache, no pre-import).** `import matplotlib` costs 1,288,336,316; with `font_manager` 1,373,930,913; `pyplot` the rest, up to 4,660,020,746. A cold font list adds about 2.0 G.
- **Benchmark facts (wall clock, median of three after a warm-up, the harness driver).** `pass`: 19 ms today, 19 ms with matplotlib linked, 35 ms with pyplot pre-imported. The plot program: 1,476 ms without pre-import, 354 ms with it.

**Should the snapshot pre-import matplotlib? The agent recommends yes; it is the owner's call.**

- For: a matplotlib call is 4.6 times cheaper in fuel (1.25 G against 5.81 G). The font cache question disappears, including on `root=False`. Every run sees the same frozen font list.
- Against: every call pays it, plot or not. +23.4 M fuel (+28% on `pass`), about +16 ms, +17.5 MB of snapshot and +18 MiB of initial memory per instance.
- A middle road, pre-importing only `matplotlib` and `font_manager`, was not measured.

### 5. Two carried patches are needed; the no-patch route does not stand

**Patch 1: ft2font's enums touch Python during static initialization (EXECUTED).**

- **The symptom.** The first scratch binary hung in `_initialize`, before Python started. A shadowed `poll_oneoff` showed a single clock subscription with a timeout of 3,757,750,312,715,157,504 ns (about 119 years): a wait forever.
- **The cause (READ, `src/_enums.h:55-63`).** `P11X_DECLARE_ENUM` defines a namespace-scope constant whose initializer runs `py::gil_scoped_acquire` and `pybind11::cast(...)`. In a shared library that runs at `dlopen`, after Python is up. Linked statically, it runs in the reactor's constructor pass, before `Py_Initialize`, and waits for a GIL that never comes. The disassembly of `_GLOBAL__sub_I_ft2font_wrapper.cpp` calls `pybind11::gil_scoped_acquire::gil_scoped_acquire()` (EXECUTED).
- **Upstream has already fixed it (READ).** matplotlib pull request #30291, "Migrate to Pybind11 v3" (<https://github.com/matplotlib/matplotlib/pull/30291>), merged 2026-07-24, milestone v3.12.0. Its commit `8e5591bcb3163d88bd9900ae74fc043c080aa631` deletes `_enums.h` and binds the enums with `py::native_enum` inside module init. It touches `src/_enums.h`, `src/_image_wrapper.cpp`, `src/ft2font_wrapper.cpp` and `ci/mypy-stubtest-allowlist.txt`.
- **The backport (EXECUTED).** `git apply --check` of that commit onto the 3.11.2 sdist succeeds with offsets in two files. Applied in a scratch copy: matplotlib built, `ft2font` had no static constructor left, `_initialize` returned, and every run below passed.
- **As a carried patch (INFERRED).** Spec 020's applier refuses offsets, so the patch is re-made against the 3.11.2 tarball, without the `ci/` file. Its pull-request draft records `Status: merged https://github.com/matplotlib/matplotlib/pull/30291`, and the patch is deleted when the line moves to matplotlib 3.12. It needs pybind11 3.x, which is the pin.
- **Why not a recipe.** A force-included header that pre-defines `MPL_ENUMS_H` with our own macros would avoid touching the tree. But it is a reimplementation of upstream code, hidden in a header, which §6.2 now ranks below a reviewed patch.

**Patch 2: `_qhull` needs a writable `/dev/null` (EXECUTED).**

- **The symptom.** Every `Triangulation` without explicit triangles, `tricontour` and `tripcolor` raised `RuntimeError: Could not open devnull`. `_qhull_wrapper.cpp:179` does `fopen(STRINGIFY(MPL_DEVNULL), "w")` to hide qhull's messages. A WASI guest has no device files, and a call may have no writable folder at all.
- **Not fixed upstream (READ, `main`'s `_qhull_wrapper.cpp:182`).**
- **A tried fix (EXECUTED).** Under `#ifdef __wasi__`, if the `fopen` fails, use `fopencookie` with a write function that discards (wasi-libc 33 has `fopencookie`, `fmemopen` and `open_memstream`; EXECUTED, `llvm-nm`). It is 10 added lines (scratch `work/0002-qhull-devnull-wasi.patch`). Then a good triangulation returned `(2, 3)`, collinear points raised `RuntimeError: Error in qhull Delaunay triangulation calculation: singular input data (exitcode=2)`, and `tricontour` drew. That error path is qhull's `longjmp`, so setjmp is proven in the guest too.
- **The pull request to draft.** Upstream may prefer a general fallback (when the configured devnull cannot be opened) to a WASI branch. The draft should offer that.

**So the answer to question 3:** the old memo's no-patch route does not stand. Two patches, one a backport of a merged upstream change and one new, with spec 020 landed first.

### 6. The milestone ran: pixel-identical to native

**The program (EXECUTED, `scripts/milestone.py`).** `matplotlib.use("agg")`, a 4×3 inch figure at 100 dpi, two lines, a title and a legend, then `canvas.draw()`, `savefig` to PNG and SVG, and a `savefig(dpi=-1)`.

| | wasm (all three scratch binaries) | native (PyPI wheels) |
|---|---|---|
| `__freetype_version__` | 2.14.3 | 2.14.3 |
| RGBA buffer, sha256 | `eab6d61b37105e98…` | `eab6d61b37105e98…` |
| PNG decoded pixels | equal: `True`, shape (300, 400, 4) | – |
| PNG file bytes | `b8759b7b…`, 22,439 bytes | `7125804b…`, 20,926 bytes |
| SVG with `svg.hashsalt = "wasi"` | `00299ff93b700a99…` | `00299ff93b700a99…` |
| `dpi=-1` | `ValueError: dpi must be positive` | the same |

- **The PNG files differ only in their deflate stream (EXECUTED).** Native Pillow reports zlib `1.3.1.zlib-ng`; ours is zlib 1.3.1. The decoded pixels and the `Software` and `dpi` chunks are equal. So the judge compares decoded pixels, or the RGBA buffer, never PNG bytes.
- **The SVG is byte-identical once its random id salt is fixed (EXECUTED).** Without `svg.hashsalt`, ids come from a random salt and differ run to run.
- **The same run also showed (EXECUTED, `e4`, pre-imported snapshot):** mathtext drew; PDF and PS saved; `contourf` returned a `QuadContourSet`; JPEG raised `OSError: encoder jpeg not available` (as intended for a zlib-only Pillow).
- **Not exercised:** contourpy's `threaded` algorithm with `thread_count=2` returned a result, but a 5×5 grid may never start a thread. What a failed `std::thread` does there is untested.

### 7. Other risks the specification must handle

- **Same bytes from any host (spec 012; INFERRED, not run).** The pre-imported snapshot holds `fontManager.ttflist`, built by walking `mpl-data/fonts` with `os.walk`, whose order is the host filesystem's. APFS and ext4 may order differently, and the snapshot's bytes with them. The Linux rebuild gate will show it. Also, the scratch build used no `-ffile-prefix-map`, and contourpy's `_build_config.py` carries paths (finding 2).
- **A new failure class: static constructors that call Python.** Patch 1 fixes the one found. A later version could bring another. A judge check that the plain reactor's `pass` exits catches any such hang; the runner's deadline turns it into `"deadline"`.
- **`-pthread` adds a host requirement silently.** A check that `python.wasm`'s `target_features` has no `+atomics` keeps it out. The scratch binary's features are the same list as today's (EXECUTED): EH and setjmp add no new feature.
- **The data path follows the zip's name** (`python315.zip`), as the zip itself does. A minor version change moves both.

## What it decides

1. **The versions:** the old memo's set, with FreeType, HarfBuzz and libraqm held at matplotlib's own wrap versions for pixel parity, and Pillow 13.0.0.
2. **The data:** a read-only runtime grant at `/usr/local/lib/python315.zip/matplotlib/mpl-data`, added by the runner on every call; matplotlib's code stays in the zip. Recommended carrier: the stdlib zip itself, extracted once per process.
3. **Patches:** two, carried under spec 020: the backport of #30291, and the `_qhull` devnull fallback with a new upstream pull request drafted.
4. **The milestone oracle:** the RGBA buffer and decoded PNG pixels equal native's; the SVG equal with a fixed salt.
5. **The estimate (INFERRED).** The scratch build took about an hour of agent time end to end. The specification's real cost is the recipe, cross-host determinism, the runner's second grant and the judge: days, not the old memo's two to four weeks.

### The smallest useful first milestone

**M1 (one specification):** `import matplotlib; matplotlib.use("agg")`, `plt.plot(...)`, `savefig` to PNG in a granted folder, and the RGBA buffer equal to native; `dpi=-1` raises `ValueError`; a kiwisolver error raises a Python exception. It needs:

- the five C libraries (qhull because matplotlib's configure requires it);
- matplotlib's `ft2font`, `_path`, `_image`, `_backend_agg`, `_c_internal_utils`, `_tri` and `_qhull`, kiwisolver, and Pillow's `_imaging`, `_imagingmath` and `_imagingmorph`;
- cycler, pyparsing, packaging and fonttools;
- patch 1.

`matplotlib.tri`'s triangulation and contourpy would be recorded as known gaps in `tests/known_gaps.toml`, each naming its closer.

**M2:** contourpy (its stand-in metadata and the `_build_config.py` rewrite) and patch 2. Then `contour`, `contourf`, `tricontour` and SVG/PDF goldens.

M1 and M2 could also be one specification. Everything in both was built and run here.

### The ordered steps for the specification

0. **Spec 020 lands** (the applier and the rules). Spec 021 carries the first patch; matplotlib's are next.
1. **Pins** (`downloads/SHA256SUMS`, below; `line.conf` gains the three `PKGCONF_WHEEL` host keys).
2. **A step after 35 for the plot libraries:**
   - FreeType: meson, `-Dzlib=internal -Dpng=disabled -Dharfbuzz=disabled -Dbrotli=disabled -Dbzip2=disabled -Dmmap=disabled -Dtests=disabled`;
   - HarfBuzz: meson with matplotlib's own option list (`extern/meson.build`), plus `-DHB_NO_PRAGMA_GCC_DIAGNOSTIC_ERROR -D_WASI_EMULATED_MMAN` (the header compiles; `HAVE_MMAP` stays undefined, so no mmap is linked);
   - SheenBidi, then libraqm with `-Dsheenbidi=true -Dtests=false`;
   - qhull: the 17 `libqhull_r` files with `-D_WASI_EMULATED_PROCESS_CLOCKS`;
   - C flags `-fwasm-exceptions -mllvm -wasm-enable-sjlj -mllvm -wasm-use-legacy-eh=false`; C++ flags `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false`; `-ffile-prefix-map`;
   - `scripts/wasi-cc` drops `-pthread` (numpy and pandas never pass it, EXECUTED by `grep`, so their bytes do not change).
3. **Pillow and kiwisolver**, compiled directly (finding 2), against step 30's zlib.
4. **matplotlib (patched) and contourpy** with meson: `-Dsystem-freetype=true -Dsystem-libraqm=true -Dsystem-qhull=true -DrcParams-backend=Agg -Db_lto=false -Dmacosx=false`, a `devnull` property, the pinned `pkgconf`, pybind11's `pkgconfig` folder, the `setuptools_scm` stand-in, and for contourpy `-Dwerror=false` and the meson-python metadata stand-in. Install with `--tags python-runtime,data` and `-Dpython.bytecompile=-1`.
5. **Step 60:** inittab names from the install paths (`ft2font` and the others build in `src/`); `.deps` lines that are `-l`/`-L` are honoured (qhull); `-lsetjmp`; `_tkagg` left out.
6. **Step 70:** the new trees and wheels; `mpl-data` as plain members; contourpy's `_build_config.py` rewritten; fontTools' `.data/` skipped.
7. **Step 80:** `PREIMPORT` gains `os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"`, `import matplotlib, matplotlib.pyplot`, then the variable removed (EXECUTED in that form); Wizer gets `--dir <mpl-data>::/usr/local/lib/python315.zip/matplotlib/mpl-data`; `MANIFEST`'s `x-preimport` and `x-wizer` lines say so. (Only if the owner says yes to pre-import.)
8. **The runner:** extract the data once per process into a private, checked folder; grant it read-only at the path on every call, with spec 017's identity check; README contract line and the snapshot difference of finding 3.
9. **Checks, each seen failing first:** the milestone against a native golden (RGBA hash, decoded PNG pixels, SVG with a fixed salt); `dpi=-1`; the kiwisolver error; the data grant refuses writes; a program that does not use matplotlib runs without the grant; no `+atomics` in `target_features`; the imports are still WASI plus the door; and in M2 the qhull error and `tricontour`.

### The new pins

Every hash is EXECUTED: the downloaded bytes, checked with `shasum -a 256 -c`.

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
# header-only, compiled in (so their notices ship too)
b8488090f8acffbcb6b5d6a85571a6827a0a2981ffb75e5a0b27b87c4a6b7dd0  pybind11-3.1.0-py3-none-any.whl
7ca132b6ef6187384738804bd3a453d4eab7e3274df6dcd35e5d92aae3404717  cppy-1.3.1-py3-none-any.whl
# pure Python, into the zip
85cef7cff222d8644161529808465972e51340599459b8ac3ccbac5a854e0d30  cycler-0.12.1-py3-none-any.whl
ece8c00a69cf01b45d0b1dedabb469c90d8caf996d4fda40f147627a122849a4  pyparsing-3.3.3-py3-none-any.whl
d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c  packaging-26.3-py3-none-any.whl
4304f03ed7f4ba000a8dcc941ad854bfa52e2f3b6112b8f099b6f431cf98e701  fonttools-4.67.0-py3-none-any.whl
# build tool, one per build host (hashes from PyPI's JSON; only the macOS one was used here)
47cbf6889d84297b9a4e1741ae016daa4e198f3ec8bab7ce74554cc50b77cce4  pkgconf-3.0.7.post0-py3-none-macosx_11_0_arm64.whl
4ece8d4e650ee172ddadff762ad31a590a4d91a070806aee09eb92a89e67f559  pkgconf-3.0.7.post0-py3-none-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl
bd3ee4b5294a888d58462324cb83b7c0bc7150cc15b64b36aaf983e4b0ab90d5  pkgconf-3.0.7.post0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl
```

- The pkgconf wheels were not downloaded; the scratch build used Homebrew's `pkg-config`. Their hashes are PyPI's (EXECUTED, `curl`), not checked against bytes.
- No longer needed, against the old memo: setuptools, setuptools_scm (a recipe stand-in) and meson-python (a metadata stand-in).
- qhull's URL is GitHub's archive (finding 1).

### Questions for the owner

1. **Pre-import matplotlib in the default snapshot?** It makes a plotting call 4.6 times cheaper and removes the font-cache problem. Every call pays +23.4 M fuel (+28% on `pass` against the same binary without pre-import, all of it in teardown), about +16 ms, +17.5 MB of snapshot and +18 MiB of memory. *Recommended: yes,* with the cost stated in the release memo.
2. **Two licences compiled in that the 2026-10-16 approval did not name:** pybind11 (BSD-3-Clause) and cppy (BSD-3-Clause, Nucleic). Both are header code that ends up in `python.wasm`. *Recommended: approve,* as numpy's BSD-3-Clause was. The approved list (FreeType's FTL, Qhull, SheenBidi's Apache-2.0, the fonts, and the old memo's table) still covers the rest; §4.12's text could record it all at once.
3. **Patch 2's upstream pull request** follows spec 020's flow: the agent drafts it, the owner sends it. No new decision; listed so it is not missed.

Not a question: where the data's bytes travel (inside the zip, or a new artifact) is the specification's choice; the zip keeps §4.6 as it is.

## Where it stopped

- **Not run on Linux.** No cross-host byte comparison of the scratch artifacts, so the font-list order risk (finding 7) is open.
- **Not run through `wasi_python.run`.** It refuses the data grant to an embedder by design; the runner change is the specification's.
- **Not run:** `import matplotlib` on the plain reactor with `root=False` and no `/tmp`; a `std::thread` start inside contourpy; the middle pre-import road; the zip-with-`mpl-data` size and its plain-reactor start-up cost.
- **pkgconf wheels not downloaded.**
- **Litter in the main tree's `build/`.** Probe runs of the host Python with `-I` (which ignores `PYTHONDONTWRITEBYTECODE`) wrote about ten `.pyc` files under `build/tools/python/lib/python3.15/__pycache__` (git-ignored). Fifteen such folders were already there. Step 60's and 70's `host_from_source` removes them before marshalling, so build bytes are unaffected.
- The scratch artifacts, the patched scratch tree, both patch files and every probe script stay in `…/scratchpad/mpl-research/`.

## One line

matplotlib 3.11.2 builds and runs on the current line, pixel-identical to native, with its data in a read-only runtime grant at the path it already computes. It needs two carried patches (a backport of upstream's merged enum fix, and a `/dev/null` fallback for qhull), `-pthread` removed, and the owner's call on pre-importing it into the snapshot.
