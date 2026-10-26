# Choosing packages: profiles, the import path, and what a developer can pick today

- **Status:** research with a recommendation, 2026-10-26. Research only: nothing in `src/`, `tests/`, `scripts/`, `recipes/` or the documents changed, apart from one pointer line added to the placeholder memo `2026-10-16-build-time-profiles-of-the-core-c-libraries.md`. No build and no judge ran. The memo commits the project to nothing; the decisions are in section 9.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Fable 5.1). Box: one session.
- **The direction it answers,** the owner's words of 2026-10-26: "research a way to make the installed packages of wasi-python more customizable? Ideally a dev could pick their dependencies instead of just having a single stack."
- **Stands on:** the constitution (§2's principle on profiles, §3, §4.3, §4.6, §4.15); the roadmap's line "Build-time profiles beyond the default"; `2026-10-16-build-time-profiles-of-the-core-c-libraries.md` (the placeholder this memo partly fills); `2026-10-18-read-only-code-on-the-import-path.md` and spec 054 (the `import_path=` argument); `2026-10-17-what-else-the-default-profile-carries.md` (the per-member and resource costs of the zip; pytz at 155 G fuel from the zip); `2026-10-18-one-pre-import-rule-for-every-package.md` and decision 34; the owner's decision 93 ("the dev building an app with wasi python would define all of the imports and code and libraries upfront"); `2026-10-22-what-the-prior-art-does-and-does-not.md`; `2026-10-17-market-research-use-cases.md`.
- **Evidence:** the folder `2026-10-26-choosing-packages-profiles-and-the-import-path/` beside this memo: `probe.py`, `probe2.py`, `probe3.py` and their `*-output.txt` (the guest runs), `wasm_sections.py`, `dump_names.py`, `attribute2.py` and `wasm-sections.txt`, `attribution2.txt` (the binary read), `zip-breakdown.txt` (the zip read). The downloaded wheels, the unpacked folders and the function-name table (14 MB) stayed in the session's scratchpad: artifacts never live in git.
- **Repository state:** `dev` at `d2b406f`. The guest runs used the **released 0.1.0 set**, installed from PyPI into a scratch environment with `uv` (`wasi_python-0.1.0-py3-none-any.whl`, 98,332,122 bytes; wasmtime-py 49.0.0; `python.wasm` `d4192605…`, 99,421,513 bytes; `python-snapshot.wasm` `879bdb62…`, 104,517,748 bytes; `python-stdlib.zip` `a7b8f7cb…`, 53,915,154 bytes, each as its `SHA256SUMS` names it). Host: a Linux x86_64 container with four cores and 15 GB, CPython 3.12 under uv. The repository's own tree was only read.
- **Labels:** EXECUTED (a command run here, its output in the evidence folder), READ (a file in this repository, a clone's file, or a web page named by URL), INFERRED (reasoning from those).

## Terms

- A **compiled package** has C, C++, Cython or Rust in it. Here its modules are linked into `python.wasm` as *builtin modules* at build time (step 60). A **pure package** is Python only; here its files sit in the stdlib zip as bytecode (step 70).
- A **profile** is a named artifact set with its own choice of compiled packages, built, judged and published by the project (constitution §2).
- The **import path** is `sys.path`. `import_path=` (spec 054) puts folders and zips from a **read-only grant** on it, after the stdlib zip.
- **Fuel** is wasmtime's count of guest instructions; a G is a thousand million.
- **dlopen** is the C call that loads a shared library at run time. `wasm32-wasip1` has none.

## 1. The short version

1. **The question splits in two, and the two halves have different answers.** A pure package can already be the developer's choice, today, with no build: install it into a folder on the host, grant the folder read-only, name it in `import_path=`. A compiled package cannot be added or removed after the link, by anyone, on this target (section 2). So "pick your compiled packages" can only mean "pick a profile", and profiles are the roadmap's existing line.
2. **Pure packages from the import path work, and the cost has one lever: bytecode.** rich, faker, python-slugify, pytz and plotly, none of them in the set, ran from a read-only folder on 0.1.0 (EXECUTED). Imported from source, rich costs 2.0 G fuel and faker 4.9 G; after one `compileall` run *inside the guest* through a writable grant, 0.7 G and 1.05 G. A `.whl` file works on the import path as it is, and is the slowest form (3.5 G and 9.2 G). pytz, unusable from the zip (155 G in the 2026-10-17 memo), costs 0.17 G from a folder; plotly, which fails from a zip, works from a folder (section 4).
3. **The released binary is one quarter CPython and three quarters packages.** By function names in the binary, scipy is about 19% of the code, pandas 14.5%, scikit-learn 8.6%, numpy 7.8%, OpenBLAS 7.4%, statsmodels 4.7%, CPython itself about 8%, the plot stack about 6% (EXECUTED, section 3). The zip is 53 MB of which the standard library is about 6 MB; sympy alone is 8.6 MB and the matplotlib stack 9.4 MB.
4. **Profiles are the only way to a smaller compiled set, and they cost a release run and a wheel each.** The dependency graph gives a lattice of four or five sensible profiles, not a free choice (section 6). The 0.1.0 wheel is 98.3 MB against PyPI's 100 MB default per file (READ), so a second set cannot ride in the same wheel: profiles force a decision on how the wheel carries a set (section 6.4).
5. **Nothing happened in 2026 that makes run-time loading of compiled code an option on `wasm32-wasip1`.** wasi-sdk's shared libraries exist and are "not as fully baked as static linking"; the dynamic-linking ABI says "there is no stable ABI yet"; no WASI runtime ships a loader; C++ exceptions, which matplotlib, scipy and contourpy use, do not cross shared libraries (READ, section 2).
6. **Recommendation** (section 8): make the pure-package route a first-class, documented feature with one small helper that compiles a library folder in the guest, and one check that names a missing compiled dependency early. Then build the first profile the placeholder memo asked for, as a specification, once the owner has chosen the wheel strategy. Do not build link-on-demand or run-time loading.

## 2. Two kinds of package, and why the wall is where it is

**What the build does today (READ).** `scripts/build.sh` runs one step per compiled package (`40_numpy.sh` to `59_statsmodels.sh`). Step 60 lists their archives, generates one inittab (`scripts/gen_inittab.py`: 11 packages, their modules registered by dotted name) and links one reactor. Step 70 lists each package's Python tree and each pure wheel, and packs one zip. Step 80 snapshots the reactor beside that exact zip. So the set of compiled packages is fixed at step 60, and the set of pure packages at step 70, and the snapshot binds the two.

**Why a developer cannot add compiled code later (READ).** The guest has no `dlopen` (`docs/reference/limitations.md`; `2026-10-16-build-time-profiles-of-the-core-c-libraries.md`). The state of the art in 2026, read on the web (the search is in the evidence folder's method; the pages are named):

- wasi-sdk's README: "Dynamic linking is supported but not as fully baked as static linking. There might be obscure bugs in some situations related to dynamic linking." Shared builds of libc and libc++ ship behind `WASI_SDK_BUILD_SHARED` ([wasi-sdk README](https://github.com/WebAssembly/wasi-sdk/blob/main/README.md), READ).
- The dynamic-linking ABI: "This ABI is still a work in progress. There is no stable ABI yet." The loader it describes (reserve memory at `__memory_base`, a table at `__table_base`, fill the GOT, call `__wasm_apply_data_relocs`) is implemented by Emscripten and toywasm; the document names no WASI runtime loader ([tool-conventions/DynamicLinking.md](https://github.com/WebAssembly/tool-conventions/blob/main/DynamicLinking.md), READ).
- The CPython guest-languages SIG's notes of August 2026, as the search summarised them (the page itself is on a host this session cannot reach, so this is READ at one remove): cooperative threading may work with shared libraries in the next wasi-sdk, "C++ exceptions probably won't, and may need significant LLVM changes", and wasi-sdk 34.0-rc.1 "doesn't yet handle shared library linking well" ([SIG notes](https://hackmd.io/@NXXwAQZbQ8CTpJXGoJcJ8w/BkxButqQ6)).
- componentize-py links `.so` libraries into one component at build time and says "the application can only import dependencies during build time" ([componentize-py README](https://github.com/bytecodealliance/componentize-py/blob/main/README.md), READ). Its releases since 0.3 build on "a temporary fork of WASI-SDK which enables both shared library support and dlopen/dlsym" ([PyPI page](https://pypi.org/project/componentize-py/0.4.1), READ). That is the component model and preview 2, not this project's one target (constitution §4.3).
- Wasmer's WASIX has `dlopen` through a PIE main module and side modules ([Wasmer blog](https://wasmer.io/posts/dynamic-linking-in-wasm-wasix), READ). WASIX is Wasmer's own target, not `wasm32-wasip1`; the 2026-10-17 market memo already said "do not chase `pip install` at run time or dynamic linking".
- Pyodide, the project that does let a user load binary packages at run time, does it with Emscripten's dynamic loader inside a JavaScript engine, from wheels built for Emscripten and fetched from a CDN or PyPI by `micropip` ([pyodide loading-packages](https://github.com/pyodide/pyodide/blob/main/docs/usage/loading-packages.md), READ). This project exists because that needs a browser or Node (constitution §1).

So for compiled code the answer is the one the constitution already gives: a profile, "its own artifact set, built, judged and published, chosen by name and never assembled on a user's machine" (§2). What this memo adds is the measurement of what the profiles would weigh, what they would cost, and what a developer can do without them.

**INFERRED:** even if a WASI `dlopen` existed, two of this project's own choices would stand in its way. The snapshot freezes the interpreter with its import state, so a module loaded after the snapshot would have to be loaded again on every call; and the wall (§4.4: WASI and one door) admits no loader import. A run-time route is therefore not a near-term option here, whatever the toolchain does.

## 3. What the released set is made of (EXECUTED)

### 3.1 The binary

`python.wasm` (99,421,513 bytes) by section (`wasm_sections.py`; `wasm-sections.txt`):

| section | bytes |
|---|---|
| code (89,060 function bodies) | 74,345,066 |
| data | 10,747,266 |
| custom `name` (every function's name) | 14,091,563 |
| elem, type, function, the rest | about 240,000 |

The `name` section is 14.2% of the file. It is not this memo's question; it is noted because any size work on the binary should know it is there.

The code bodies, attributed to the component that compiled them (`attribute2.py`; `attribution2.txt`). The method: a name whose owner is certain is an *anchor* (Cython's package-qualified names, a library's prefix such as `qh_`, `hb_`, `xml[A-Z]`, `sqlite3`, CPython's `Py*`, OpenBLAS's Fortran-style `dgetrf_`); wasm-ld writes functions in input order, object by object, so a function between two anchors of one owner is that owner's. 73% of the code is anchored directly; 12.2% sits between two different owners and is left unattributed (mostly Cython's own module-initialisation and runtime functions, which belong to the Cython packages in proportion). The table is therefore good to about one percentage point per row, not to the byte.

| component | code bytes | share |
|---|---|---|
| scipy (Cython, C, C++: HiGHS, xsf, ducc0, PROPACK, ARPACK, SuperLU) | 14,102,174 | 19.0% |
| pandas | 10,807,819 | 14.5% |
| unattributed (Cython runtime and module init, between owners) | 9,062,731 | 12.2% |
| scikit-learn (with libsvm, liblinear) | 6,372,928 | 8.6% |
| CPython | 5,970,761 | 8.0% |
| numpy | 5,814,258 | 7.8% |
| OpenBLAS (numpy's and scipy's BLAS and LAPACK) | 5,528,981 | 7.4% |
| statsmodels | 3,481,032 | 4.7% |
| libc++, libc++abi, libunwind | 2,815,761 | 3.8% |
| pybind11 (matplotlib, contourpy, scipy) | 2,305,740 | 3.1% |
| lxml | 1,737,838 | 2.3% |
| SQLite | 1,441,661 | 1.9% |
| matplotlib (its own C++ and Agg) | 964,916 | 1.3% |
| libxml2, libxslt | 942,605 | 1.3% |
| HarfBuzz | 907,330 | 1.2% |
| FreeType | 487,280 | 0.7% |
| regex | 388,867 | 0.5% |
| qhull | 303,231 | 0.4% |
| wasi-libc, compiler-rt | 229,769 | 0.3% |
| Pillow | 215,293 | 0.3% |
| contourpy | 150,218 | 0.2% |
| xz, bzip2, zlib, kiwisolver, SheenBidi, libraqm | 341,747 | 0.5% |

Read by stack (INFERRED, each row's unattributed share added in proportion): the interpreter with its stdlib libraries (CPython, libc, SQLite, zlib, bzip2, xz, a share of libc++) is about **10 MB of code**; numpy with pandas and OpenBLAS about **25 MB**; the plot stack (matplotlib, pybind11's share, HarfBuzz, FreeType, qhull, Pillow, contourpy, kiwisolver) about **5 MB**; scipy with scikit-learn and statsmodels about **29 MB**; lxml with libxml2 and libxslt about 3 MB; regex 0.4 MB. The whole file scales with the code (data and names are spread the same way), so a CPython-only reactor would be roughly **15 MB**, against 99 MB today. The spike memo's 2026-10-16 figure, numpy and pandas at 40% of a binary that then held only them, agrees with this.

### 3.2 The zip

`python-stdlib.zip`: 6,262 members, 53,056,256 compressed bytes (`zip-breakdown.txt`). The largest top-level folders:

| folder | members | compressed bytes |
|---|---|---|
| sympy | 879 | 8,569,359 |
| matplotlib (with `mpl-data.zip`) | 109 | 6,935,845 |
| scipy | 607 | 5,568,328 |
| statsmodels | 501 | 3,710,351 |
| pandas | 315 | 3,618,968 |
| sklearn | 410 | 3,216,294 |
| the stdlib's top-level modules | 161 | 2,431,493 |
| fontTools | 344 | 2,261,676 |
| networkx | 289 | 1,736,985 |
| numpy | 181 | 1,495,524 |
| reportlab | 143 | 1,476,946 |
| narwhals | 164 | 1,097,113 |

Summing every package folder gives about 47 MB; the standard library itself is about **6 MB compressed** (INFERRED from the table). So a profile's zip would be about 6 MB plus its packages' Python halves: numpy and pandas about 5 MB; the plot stack with fontTools and mpl-data about 9.4 MB; scipy, scikit-learn, statsmodels with patsy and formulaic about 13 MB; sympy and mpmath 9.3 MB on their own.

## 4. Pure packages from the import path, measured (EXECUTED)

Every call below ran `wasi_python.run` on the released 0.1.0 set, fuel metered, on the snapshot unless marked plain (`probe.py`; `probe-output.txt`). The packages: rich 15.0.0 (with pygments, markdown-it-py, mdurl), faker 40.43.0, python-slugify 9.1.3 (with text-unidecode), pytz 2026.5, plotly 7.1.0; none is in the set. Three forms of the same library were tried: the `.whl` files themselves on the import path; the wheels unpacked into one folder (what `pip install --target` or `uv pip install --target` makes); and that folder after one `compileall` run inside the guest.

| call | fuel | wall (this host) |
|---|---|---|
| `-c pass`, no import path | 53,438,780 | 40 ms after the first call |
| `-c pass`, eight `.whl` entries | 55,017,164 | 40 ms |
| `-c pass`, one folder entry | 54,854,415 | 42 ms |
| rich: a table rendered, from the `.whl` files | 3,542,296,081 | 1.0 s |
| rich, from the unpacked folder (source) | 2,035,132,250 | 0.69 s |
| rich, from the folder compiled in the guest | 705,608,370 | 0.34 s |
| faker: a seeded name, address and date, from the `.whl` files | 9,168,879,612 | 2.1 s |
| faker, from the unpacked folder (source) | 4,940,261,031 | 2.3 s |
| faker, from the folder compiled in the guest | 1,051,739,142 | 1.5 s |
| python-slugify, from the `.whl` | 446,010,187 | 0.17 s |
| pytz, `timezone('Europe/Paris')`, from the compiled folder | 166,234,558 | 0.30 s |
| plotly, a bar figure to JSON and HTML, from a source folder (`probe3.py`) | 3,622,795,045 | |
| `compileall` of the folder, once, through a writable grant | 34,976,485,272 | 13.3 s |

Findings:

1. **It works as documented, with no change.** Each package imported, its `importlib.metadata` version read (from the `dist-info` beside it), and its output was right: faker's seeded output is the same string in every form. The folder made by `uv pip install --target lib/ rich faker python-slugify` imported as it stood (`probe2.py`: 4,897,969,801 fuel for the three, from source).
2. **A wheel file is an import-path entry.** zipimport reads a `.whl` as any zip, so the raw downloads work with no unpacking. It is the slowest form: every module is compiled from source on every call, and the zip's directory is read too.
3. **Bytecode is the lever, and only the guest can make it.** A `.pyc` is used only when its magic matches the guest's CPython 3.15 (`cpython-315`). The developer's host Python is 3.11 to 3.14 and writes `.pyc` files the guest ignores (READ, the 2026-10-18 memo, finding 3). But `compileall` *inside the guest*, with the folder as a writable grant for that one call, wrote 1,279 `.pyc` files in 13 seconds, and the folder then read-only cut rich's import to a third and faker's to a fifth. The folder grew from 24 MB to 31 MB.
4. **A folder costs nothing at start.** One folder entry adds 1.4 M fuel to a bare call; eight wheel entries add 1.6 M. The per-member cost the 2026-10-17 memo measured (about 78,000 fuel per zip member on the plain binary) is the stdlib zip's central directory, which these entries do not touch until an import reaches them.
5. **A folder reaches what a zip cannot.** pytz reads hundreds of zone files by resource; from the stdlib zip the 2026-10-17 memo measured 155 G fuel, and the project left pytz out (decision 47). From a folder the same call costs 0.17 G. plotly reads its validators by file path and fails from a zip (the same memo); from a folder it builds a figure and writes JSON and HTML. So the folder route is not only "your own helpers": it is the route for the pure packages the project will never put in the zip.
6. **Sessions keep the import.** In a `Session` over the compiled folder, the turn that imports rich and its console costs 207 M fuel and the turn that renders costs 46 M (`probe2.py`).
7. **The plain binary pays the same for the package and more for the start** (`-c pass` 271 M; rich compiled 1.06 G; faker compiled 1.43 G). The snapshot is the better host for this route as for every other.
8. **The shadowing rule holds.** With the folder on the path, `numpy.__spec__.origin` is still the zip's (`/usr/local/lib/python315.zip/numpy/__init__.pyc`): a module the set has stays the set's.
9. **The failure for a compiled dependency is late and generic.** `import pydantic_core` from a folder that lacks it ends in CPython's `ModuleNotFoundError … did you forget to add the site-packages directory to sys.path`, which points the developer the wrong way (there is no site-packages). A folder that *holds* a `pydantic_core*.so` would fail the same way, since the guest never loads a `.so`.

**INFERRED:** on this measure, the pure half of "pick your dependencies" is a documentation and ergonomics problem, not a build problem. The owner's decision 93 placed it exactly here: the developer defines the libraries up front; the import path is the place; mounts stay refused.

## 5. What would make the pure route a feature rather than a trick

Each item is small and lives in the runner or the docs; none touches the guest, the build or the artifact set, so none needs a pre-build review (constitution §5.6). Sizes are INFERRED.

1. **A documented recipe on the packages page and a how-to.** Today `docs/reference/packages.md` says, in three sentences, that a pure package "can come from a read-only grant named in `import_path=`". The recipe is: `uv pip install --target lib/ <packages>` (or pip's `--target`), compile once (item 2), grant `lib/` read-only, pass `import_path=["/lib"]`. With the table above and the two packages that work only this way (pytz, plotly), and the rule that a name the set has is always the set's.
2. **A compile helper.** `wasi-python compile-library <folder>` on the command line and `wasi_python.compile_library(folder)` in the API: one guest call that runs `compileall` over the folder as a writable grant, under the runner's limits, and reports how many files it wrote. Without it a developer needs to know that the host's `.pyc` files are ignored and that only the guest can write usable ones. It is a thin wrapper over `run`; it adds no power `run` does not have (the §3 test for a runner feature). About 40 lines and a check.
3. **An early, specific refusal for compiled code.** The runner can walk an import-path folder once per call cheaply enough (`_places.py` already walks the grants for its layout checks) and refuse an entry that holds a `.so`, `.pyd` or `.dylib` with a message that says the guest loads no shared library. A deeper check, reading each `dist-info/METADATA`'s `Requires-Dist` against the set's packages and warning of a compiled requirement the set lacks, would turn `pydantic`'s late `ModuleNotFoundError: pydantic_core` into a refusal that names it. The second is about 60 lines and belongs behind the first. Both are refusals of an argument before any work, in the style of the grant checks.
4. **A line in the version string's facts.** `python3 --version` lists what the platform lacks (constitution §4.11); "no shared libraries: compiled packages are the set's" belongs there.

Not recommended: a project-run registry of "known-good pure wheels", a `pip`-like command inside the guest, or any download by the runner. Each pulls toward a development environment (§3) and an unpinned input (§4.2).

## 6. Profiles: what the compiled choice can be

### 6.1 The lattice

The compiled packages depend on each other, so a profile is a cut through a small graph, not a free list (READ: the build steps' prerequisites in `60_link.sh`, `70_zip.sh`; the package memos):

- numpy needs OpenBLAS (spec 100) and the stdlib libraries; pandas needs numpy (with python-dateutil, tzdata, six);
- matplotlib needs numpy, Pillow, kiwisolver, contourpy, qhull, FreeType, HarfBuzz, SheenBidi, libraqm, and the pure fontTools, cycler, pyparsing, packaging; seaborn needs matplotlib and pandas;
- scipy needs numpy and OpenBLAS; scikit-learn needs scipy, joblib, threadpoolctl; statsmodels needs scipy and pandas, with patsy and formulaic;
- lxml, regex, SQLite, bzip2, xz stand alone; python-docx and python-pptx (not yet in the set) would need lxml; reportlab needs Pillow.

That gives this lattice (INFERRED sizes, from section 3; the whole-file size is the code share scaled to today's 99 MB):

| profile | compiled packages | `python.wasm` | zip |
|---|---|---|---|
| `core` | CPython, zlib, bz2, lzma, sqlite3, regex, lxml; every tier A pure package that needs no numpy (openpyxl, pypdf, bs4, jinja2, yaml, networkx, sympy, …) | about 15 MB | about 20 MB (6 stdlib + sympy's 9.3 + the rest); about 10 MB without sympy |
| `data` | `core` + numpy, pandas, OpenBLAS | about 50 MB | about 25 MB |
| `plot` | `data` + matplotlib's stack, seaborn, reportlab | about 57 MB | about 36 MB |
| `science` (today's default) | `plot` + scipy, scikit-learn, statsmodels | 99 MB (measured) | 53 MB (measured) |
| `full` (decision 34's name) | `science` with the stack pre-imported in the snapshot | 99 MB; a larger snapshot | 53 MB |

Two or three of these are worth having, not five (§2: "profiles stay few"). The gap that matters most is between `core` and the default: a developer who wants Python with Excel, PDF and HTML and no array stack carries 150 MB today for 35 MB of use. The gap between `data` and `science` is the second: scipy, scikit-learn and statsmodels are 40% of the code.

### 6.2 What the build needs

The steps are already one per package. What is not yet data is the two lists: step 60's archive and inittab list, and step 70's `--tree`, `--wheel` and `--metadata` lines (READ). A profile file (name, the packages, what the snapshot pre-imports) that both steps read, and that `build.sh` takes as `--profile <name>`, is the whole change to the recipe. `MANIFEST` gains a `profile` line and `assemble_artifacts.py`'s `PACKAGES` table becomes per profile. The patches, pins and recipes are shared: a profile is a selection, never a different build of a package. This is the placeholder memo's item 1 and is a build-recipe change, so its specification gets a pre-build review (§5.6).

### 6.3 What the judge needs

The judge's package list (`tests/harness/paths.py`, `PACKAGES`) and `tests/upstream/packages.toml` assume one set (READ). Each check already names its package through its golden job and its shard (`tests/release_shards.toml`: a shard per package family). A profile dimension would skip the checks of packages the set lacks, keep the ratchet per profile, and run the shards a profile has. The cost is the real one: every profile is another artifact set to build on three hosts for same-bytes, another `.cwasm` to compile per shard, and its own slice of the 38-job-wide release run (READ, the roadmap). INFERRED: `core` is cheap to judge (CPython's suite, the pure packages' suites, lxml, regex: perhaps a quarter of the run); `data` adds numpy's and pandas' suites. A release with three profiles is roughly two release runs' work, not three, because the heavy shards belong to the default.

### 6.4 What the wheel needs, and PyPI

The 0.1.0 wheel is 98,332,122 bytes (EXECUTED: PyPI's JSON). PyPI's defaults are 100 MB per file and 10 GB per project; a larger file limit is asked for on the `pypi/support` tracker, needs a release already under the limit, and is granted by volunteers after a wait that other maintainers report in weeks ([PyPI storage limits](https://docs.pypi.org/project-management/storage-limits), [pypi/support](https://github.com/pypi/support/issues/4521), READ). Question 64 (2026-10-18) said "wait on a decision until we cross the 100MB threshold"; profiles bring the threshold forward, because a wheel cannot hold two sets. The ways out (INFERRED):

1. **One distribution per profile.** `wasi-python-core`, `wasi-python-data`, each carrying its set and the same runner code, each under 100 MB; `wasi-python` keeps the default set. The runner finds the set as today (`artifact_dir()`). Simple; it multiplies the PyPI projects and the release jobs, and a developer who wants two profiles installs two runners.
2. **A thin runner wheel and the set as a separate download.** `wasi-python` carries the runner alone (about 1 MB); `wasi-python run` or the first `run()` fetches `wasi-python-set-<version>-<profile>.tar.xz` from the GitHub release, checks it against the `SHA256SUMS` the wheel carries, and keeps it in the user cache. This is how every other distribution of a large runtime works (Pyodide's CDN, Playwright's browsers). It costs the thing the README promises: `pip install wasi-python` and nothing else; and it makes the runner reach the network once, which the project has never done. The check against hashes shipped in the wheel keeps §4.2's spirit.
3. **Sets as wheels of their own.** `wasi-python-set-core`, data-only wheels the runner depends on by extra: `pip install "wasi-python[core]"`. An extra can choose a dependency, so it can choose a set; each set wheel stays under 100 MB. The runner's `artifact_dir()` would look the set up through `importlib.metadata`. Closest to today's promise; one more PyPI project per profile.
4. **Ask PyPI for a limit raise** for `wasi-python` and carry several sets in one wheel. Against: a 250 MB wheel for everyone, including those who wanted `core`; the raise is slow and not guaranteed.

Option 3 keeps `pip install` as the whole install and lets a developer name a profile with an extra. It is the recommendation below. It is the placeholder memo's item 4, and the owner's to choose (section 9).

## 7. The other routes, and why not now

- **Link on demand on the developer's machine.** Publish each package's static archives and `libpython`, and ship `wasi-python link --with numpy --with pandas` that runs `wasm-ld` and `wasmtime wizer` locally. It gives the free choice the owner asked about. Against: it is the thing §2 names and forbids ("never assembled on a user's machine"); the binary it makes was never judged, so no release promise covers it; it needs wasi-sdk's linker and the pinned wasmtime on the developer's machine (hundreds of megabytes, three platforms); and the snapshot would be made with the developer's wizer, so its byte reproducibility would be theirs to prove. Not recommended. If the owner ever wants it, it is an amendment to §2 first.
- **Build on demand in the project's CI.** A `workflow_dispatch` with a package list that builds, judges and publishes a set as a run artifact. It keeps "built and judged" and loses "few and published"; it costs a release run per request and makes the project a build service. Not recommended; noted because it is the only form of free choice that keeps the judge in the loop.
- **Run-time loading.** Section 2: no loader on this target, no stable ABI, no exceptions across libraries, and the snapshot and the wall against it. Revisit when wasi-sdk ships shared libraries with exceptions and a WASI runtime ships a loader; neither is dated.
- **A run-time switch that refuses imports.** Saves no bytes (READ, the placeholder memo). Not a profile.
- **Splitting the zip per package.** The stdlib zip could be several zips the runner mounts by name. The snapshot pays nothing for zip members it does not import (decision 34), so this saves download size only, and it breaks the snapshot's binding to one zip. Not worth a change.

## 8. Recommendation

1. **Now, as one runner specification:** section 5's items 1 to 4. The pure-package route becomes the documented answer to "I need a library that is not in the set": install into a folder, compile it once in the guest, grant it read-only, name it. The compile helper and the early refusal are the two pieces that turn today's measured behaviour into something a developer can rely on. Nothing in the guest or the build changes, so the pre-build review does not apply, and its checks are counted fuel and exit codes.
2. **Then, the first profile, as the placeholder memo planned,** once the owner has chosen the wheel strategy (section 6.4, option 3 recommended): a specification that makes steps 60 and 70 read a profile file, builds `core` as the first second profile, measures it (the placeholder's item 2), teaches the judge the profile dimension (item 3), and publishes `core` as its own set wheel with `pip install "wasi-python[core]"`. Its pre-build review is the one §5.6 requires for a build-recipe change. `data` follows if the first is wanted.
3. **Do not build** link-on-demand, build-on-demand or anything that loads code at run time.

The order matters: the pure route costs days and helps every profile; the first profile costs a release run per profile per release for as long as it exists.

## 9. Questions for the owner

1. **Which half is meant?** "A dev could pick their dependencies" is fully true today for pure packages and can only ever mean "pick a profile" for compiled ones, unless §2's principle is amended to allow assembly outside the project. Is the recommendation's reading (pure now, few profiles later, no outside assembly) the intended one?
2. **The wheel strategy for several sets** (section 6.4): set wheels chosen by an extra (recommended), one distribution per profile, a thin runner that downloads the set, or a PyPI limit raise?
3. **The first second profile:** `core` (no array stack; the lightest, and the largest gap) or `data` (numpy and pandas only; the placeholder memo's original aim)?
4. **Does the runner gain the compile helper and the import-path refusals** (section 5, items 2 and 3), given that each is a new argument or command and §4.15 asks the owner about defaults? Neither loosens a default: both refuse more and compile only what the caller names.

## One line

A developer can already pick any pure package by installing it into a folder, compiling it once inside the guest and naming it on the import path, and a compiled package can only ever be picked by choosing a profile the project built and judged; this memo measured both, found the binary is three quarters packages and the wheel is at PyPI's limit, and recommends making the pure route a documented feature now and building the first profile, `core`, behind a set wheel chosen by an extra.
