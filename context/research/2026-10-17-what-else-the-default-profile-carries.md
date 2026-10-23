# What else the default profile carries

- **Status:** executed, 2026-10-17. Research only: nothing in the build, the recipes or the judge was changed. Box: one working session; finished inside it, with what was not run listed at the end.
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), with two research sub-agents it briefed and whose reports it checked against its own runs: one read the hosted sandboxes' package lists and the usage studies (web, READ), one studied native and Rust extensions on `wasm32-wasip1` (web, READ, and link tests EXECUTED in its scratch).
- **The direction it answers,** the owner's words of 2026-10-17 (`decisions.md`, "The roadmap"): "we should probably consider what other libraries we should include for our v0.1.0 default profile."
- **Feeds:** `roadmap.md` (the default profile's row "others: to be chosen"); the specifications ordered at the end; the owner's questions below.
- **Stands on:** `2026-10-17-trimming-fonttools.md` (about 76,490 instructions per zip member on every plain start), `2026-10-17-matplotlib-on-the-current-line.md` (matplotlib M1: +681 zip members, Pillow in), `2026-10-17-what-scipy-needs.md` (the 0.92 Pyodide-to-ours size ratio; no threads), `2026-10-16-build-time-profiles-of-the-core-c-libraries.md` (no `dlopen`: native code is chosen at link time), `2026-10-17-market-research-use-cases.md` (what hosted tools ship), `2026-10-17-the-runtime-for-agent-code.md` (the import path is the stdlib zip only).
- **Evidence:** `2026-10-17-what-else-the-default-profile-carries/` beside this memo: `scripts/` (every script run), `outputs/` (every number quoted), `web/` (the package lists fetched). The wheels, the scratch zips and the Rust link-test trees stayed in the session scratchpad (artifacts never live in git).
- **Repository state:** `main` at `a5c7098`; the guest runs used `build/artifacts/` (CPython 3.15.0, numpy 2.5.2, pandas 3.0.6, the 0.1.0a3 line) read-only, through `wasi_python.run` with an `Artifacts` whose stdlib zip was a scratch copy. The main tree's judge and `scripts/build.sh` were not run.

## The question

Which libraries, beyond CPython, numpy, pandas, matplotlib and scipy, should 0.1.0's default profile carry? For each candidate: what agent code uses it for, what it is made of, what it costs here, whether it works with no network and no threads, what the hosted code interpreters ship, and how often generated code imports it.

Terms used below:

- **Member:** one file in the stdlib zip. Step 70 (`scripts/steps/70_zip.sh`, `scripts/make_stdlib_zip.py`) packs pure-Python wheels as members: each `.py` becomes a `.pyc`, tests and sources are skipped, and the wheel's `.dist-info` is dropped.
- **Plain start:** a call on the plain reactor (`snapshot=False`). zipimport reads the whole central directory of the zip on every plain start, so each member costs fuel there. The snapshot already holds the directory and does not pay it.
- **Pure / native:** pure means Python only, packable by step 70 with one pin and one `--wheel` line. Native means C, C++, Rust or Fortran, compiled to an archive and linked into `python.wasm` as builtins (step 60's pattern).
- **Stand-in:** a small module of ours in the zip in place of an upstream one (as `recipes/ctypes_stub.py` stands in for `ctypes`). A recipe, not a patch (§4.1).

## Method

- **Every candidate, measured as step 70 packs it (EXECUTED).** `scripts/install_each.sh` installed each of 112 distributions alone (`--no-deps`, binary wheels, CPython 3.15 where a cp315 wheel exists, else 3.14) into its own scratch folder with `uv pip install --target`. `scripts/measure.py`, run by the line's host Python 3.15.0, reads each one's metadata (version, licence, requirements), finds native files, and writes the members step 70 would write (compiled `.pyc`, deflate level 9, step 70's skip rules) to a per-package zip. Output: `outputs/measure.tsv`. Check of the rules: tzdata gives 628 members here and 627 in today's zip; numpy's Python part 182 against 181 (EXECUTED).
- **Pure candidates, run inside today's `python.wasm` (EXECUTED).** `scripts/guest_probe.py` built a zip of today's 1,751 members plus 5,609 from 58 candidate distributions (7,360 in all), then ran, on the plain reactor with fuel metered, `-c pass` twice on each zip and one small job per candidate (write and read a workbook, extract a PDF's text, parse HTML, render a template, solve an equation, and so on). Outputs: `outputs/guest/fuel.tsv`, `outputs/guest/probes.tsv` and each probe's stdout and stderr.
- **Follow-ups (EXECUTED).** `scripts/guest_followup.py`: the same zip with each wheel's `METADATA` and `entry_points.txt` kept, a writable `/tmp` (`root=True`), xlsxwriter in memory, pytz, the pandas template loader. `scripts/guest_resources.py`: the cost of a resource read on a small and a large zip. `scripts/guest_reportlab.py`: reportlab. Outputs beside them.
- **Native parity (EXECUTED).** `scripts/native_parity.py` ran seven of the probes natively (host CPython 3.15.0, the same package versions): the outputs match the guest's (`outputs/native-parity.txt`).
- **Build systems (EXECUTED: read from each sdist).** statsmodels 0.15.0 and scikit-learn 1.9.1 build with meson-python, as numpy, pandas and scipy do here; regex, markupsafe, bottleneck and numexpr with setuptools.
- **Web (READ, sub-agent, 2026-10-17).** The hosted sandboxes' lists and the usage studies; PyO3, rustc's `wasm32-wasip1` page, HubSpot's boomslang, dicej/wasi-wheels, Pyodide's recipes and its 314.0.7 wheels (sizes EXECUTED by download). Sources at the end.
- **Rust link tests (EXECUTED, sub-agent).** A Rust `staticlib` for `wasm32-wasip1` (stable rustc 1.97.1, LLVM 22.1.6, already installed on this machine) linked with wasi-sdk 33's clang 22.1.0 next to standard-EH C++ and wasm setjmp, with and without cross-language LTO, and ran under wasmtime 49. The test trees stayed in the scratchpad.

## Findings

### 1. What hosted code interpreters ship (READ)

| candidate | ChatGPT 2026 `pip list` | Claude API code execution | Gemini | AgentCore | E2B template | Pyodide 314.0.7 builds |
|---|---|---|---|---|---|---|
| openpyxl | yes | yes | yes | yes | yes | no (pure, micropip) |
| xlsxwriter, xlrd | yes, no | yes, yes | no, yes | yes, yes | no, yes | no, yes |
| python-docx, python-pptx | yes, yes | yes, yes | yes, yes | yes, yes | yes, no | no, no |
| pypdf, pdfplumber, reportlab | yes, yes, yes | yes, yes, yes | PyPDF2, no, yes | yes, yes, yes | no | no |
| lxml, beautifulsoup4 | yes, yes | no, no | yes, no | yes, yes | no, yes | yes, yes |
| jinja2, tabulate, pyyaml | yes, yes, yes | no | yes, yes, no | yes, no, yes | no | yes, no, yes |
| sympy, mpmath | yes | yes | yes | yes | yes | yes |
| networkx | yes | no | no | yes | no | yes |
| scikit-learn, joblib | yes | yes | yes | yes | yes | yes |
| statsmodels | yes | yes | no | yes | no | yes |
| seaborn | yes | yes | yes | yes | yes | micropip |
| plotly, altair | yes, no | no | no | yes, no | yes, no | micropip, yes |
| pytz, tqdm | yes, yes | yes, yes | dep, no | yes, yes | yes, dep | yes, yes |
| pyarrow, polars, duckdb | no, no, no | yes, no, no | no | yes, yes, yes | no | yes, yes, yes |
| pydantic, requests | yes, yes | no | no | yes, yes | no, yes | yes, yes |

- The Claude API's code execution tool lists exactly: pandas, numpy, scipy, scikit-learn, statsmodels; matplotlib, seaborn; pyarrow, openpyxl, xlsxwriter, xlrd, pillow, python-pptx, python-docx, pypdf, pdfplumber, pypdfium2, pdf2image, pdfkit, tabula-py, reportlab, img2pdf; sympy, mpmath; tqdm, python-dateutil, pytz, joblib. No internet. The claude.ai analysis tool runs JavaScript, not Python.
- Gemini lists 37, among them attrs, jinja2, jsonschema, lxml, openpyxl, PyPDF2, python-docx, python-pptx, reportlab, scikit-learn, seaborn, sympy, tabulate, toolz, xlrd, and no statsmodels.
- smolagents' local executor authorises only standard-library modules by default.
- **The common core:** every hosted sandbox's list (Pyodide is a distribution, not a sandbox) carries pandas, numpy, matplotlib, scikit-learn, scipy, seaborn, openpyxl, python-dateutil, sympy and mpmath, joblib and Pillow, and at least one of python-docx, python-pptx, xlrd and reportlab.

### 2. What generated code imports (READ)

- **DS-1000** (problems per library): pandas 291, numpy 220, matplotlib 155, scikit-learn 115, scipy 106, PyTorch 68, TensorFlow 45.
- **BigCodeBench v0.1.4** (1,140 tasks; tasks per external library, counted by the sub-agent from the dataset's `libs` field, `scripts/bcb.py`): pandas 426, numpy 334, matplotlib 309, sklearn 152, scipy 85, seaborn 72, requests 40, nltk 26, pytz 17, bs4 14, dateutil 11, cv2 10, statsmodels 7, PIL 6, regex 5, cryptography 4, folium 3, 2 each for lxml, sympy, docx, openpyxl, xmltodict, wordcloud, textblob, faker; yaml, chardet, shapely, geopandas, skimage 1 each.
- **"LLMs Love Python"** (arXiv 2503.17181, eight models, 526 BigCodeBench problems): numpy, pandas and matplotlib lead for every model; pandas in 58% of answers, polars 0%; seaborn 17%, plotly 0.4%.
- Reading (INFERRED): after the five already decided, the next most-used are scikit-learn and seaborn by a wide margin, then statsmodels, the HTML and Excel readers, and pytz. The office formats matter more in products (file uploads) than in benchmarks.

### 3. The candidates measured (EXECUTED: `outputs/measure.tsv`, `outputs/guest/probes.tsv`)

Members and deflated bytes are what step 70 would add (Python part only for native packages). "Guest" is the result of the probe inside today's `python.wasm`.

| package | agent use | kind | needs | licence | members | deflated | guest |
|---|---|---|---|---|---|---|---|
| openpyxl 3.1.5 (+et-xmlfile) | read/write .xlsx, `pd.read_excel` | pure | – | MIT | 195 | 512 KB | reads; writes need a writable `/tmp` (finding 4b) |
| xlsxwriter 3.2.9 | write .xlsx, charts in Excel | pure | – | BSD-2-Clause | 43 | 336 KB | works with `in_memory` and no `/tmp` |
| xlrd 2.0.2 | legacy .xls | pure | – | BSD | 11 | 143 KB | imports |
| pypdf 6.21.1 | PDF text, merge, split | pure | (AES: cryptography or PyCryptodome) | BSD-3-Clause | 61 | 827 KB | extracts text, writes; matches native |
| pdfminer.six 20260107 | PDF layout text | pure | **cryptography** (Rust + OpenSSL) at import | MIT | 183 | 6.7 MB | fails: no `cryptography` |
| reportlab 5.0.1 | write PDF reports | pure | Pillow, charset-normalizer | BSD | 192 | 2.7 MB | needs Pillow (matplotlib M1) |
| python-docx 1.2.0, python-pptx 1.0.2 | Word, PowerPoint | pure | **lxml** (C) | MIT | 231 | 1.1 MB | fails: no `lxml` |
| beautifulsoup4 4.15.0 (+soupsieve) | HTML scraping of files | pure | typing-extensions | MIT | 26 | 259 KB | works |
| html5lib 1.1 (+webencodings) | `pd.read_html` without lxml | pure | six | MIT, BSD | 38 | 234 KB | `pd.read_html(flavor="bs4")` matches native |
| pyyaml 6.0.3 | YAML | pure fallback (C optional) | – | MIT | 19 | 90 KB | works, pure loader |
| tomli-w 1.2.0 | write TOML | pure | – | MIT | 4 | 7 KB | works |
| jinja2 3.1.6 (+markupsafe) | templates, `df.style`, `df.to_latex` | pure fallback | – | BSD-3-Clause | 31 | 319 KB | renders; pandas' Styler fails (finding 4d) |
| tabulate 0.10.0 | `df.to_markdown()` | pure | – | MIT | 2 | 42 KB | fails without its metadata; works with it |
| charset-normalizer 3.5.2 | guess a file's encoding | pure fallback | – | MIT | 14 | 89 KB | works, matches native |
| xmltodict 1.0.4, defusedxml 0.7.1 | XML to dict; safe XML parsing | pure | – | MIT, PSF-2.0 | 14 | 33 KB | works |
| networkx 3.7 | graphs | pure | (scipy for pagerank) | BSD-3-Clause | 290 | 1.7 MB | works; matches native |
| sympy 1.14.0 (+mpmath 1.4.1) | symbolic maths | pure | – | BSD-3-Clause | 936 | 9.3 MB | mpmath works; sympy fails on the `ctypes` stand-in (finding 4c) |
| patsy 1.0.3 | formulas (statsmodels) | pure | packaging (M1 brings it) | BSD-2-Clause | 31 | 329 KB | needs `packaging` |
| joblib 1.6.0 (+cloudpickle) | `Parallel`, caching (sklearn) | pure | – | BSD-3-Clause | 49 | 289 KB | `n_jobs=2` falls back to serial, same result |
| threadpoolctl 3.7.0 | sklearn's thread limits | pure, uses ctypes | – | BSD-3-Clause | 2 | 29 KB | fails on the `ctypes` stand-in |
| narwhals 2.27.1 | dataframe-agnostic layer (sklearn, plotly, formulaic) | pure | – | MIT | 165 | 1.1 MB | works |
| attrs, more-itertools, toolz, typing-extensions | utilities | pure | – | MIT, MIT, BSD-3-Clause, PSF-2.0 | 46 | 332 KB | work |
| tqdm 4.70.1 | progress bars | pure | – | MPL-2.0 AND MIT | 34 | 113 KB | works |
| seaborn 0.13.2 | statistical plots | pure | matplotlib | BSD-3-Clause | 55 | 532 KB | needs matplotlib |
| plotly 7.1.0 | interactive charts (HTML) | pure | narwhals | MIT | 1,534 | 9.7 MB | fails: reads its validators JSON by file path |
| altair 6.3.0 | Vega-Lite charts | pure | jsonschema → **rpds-py** (Rust) | BSD-3-Clause | 64 (+61) | 1.1 MB | fails: no `rpds` |
| rich 15.0.0 (+pygments, markdown-it-py, mdurl) | terminal formatting | pure | – | MIT, BSD-2-Clause | 523 | 2.8 MB | works |
| pytz 2026.5 | old-style time zones | pure, 600 zone files | – | MIT | 611 | 416 KB | works but 155 G to 500 G fuel per `timezone()` (finding 4e) |
| requests 2.34.2, httpx 0.28.1 | HTTP | pure | urllib3, certifi, anyio… | Apache-2.0, BSD-3-Clause | 21, 25 (+deps) | – | no network: `_socket` has no `getaddrinfo` |
| pydantic 2.14.1 | data validation | pure + **pydantic-core** (Rust) | – | MIT | 108 | 904 KB | fails: no `pydantic_core` |
| scikit-learn 1.9.1 | machine learning | Cython + C++, OpenMP optional | scipy, joblib, threadpoolctl, narwhals | BSD-3-Clause | 415 | 3.5 MB | not built |
| statsmodels 0.15.0 (+formulaic, interface-meta, wrapt) | regression, time series, tests | Cython | scipy, patsy, formulaic | BSD-3-Clause, MIT, BSD-2-Clause | 641 | 5.1 MB | not built |
| lxml 6.1.3 | XML/HTML, docx/pptx | Cython + libxml2, libxslt | – | BSD-3-Clause; MIT; MIT | 39 | 190 KB | not built |
| regex 2026.9.29 | richer regular expressions | one C file | – | Apache-2.0 AND CNRI-Python | 4 | 87 KB | not built |
| pyarrow 26.0.0, polars 2.0.0, duckdb 1.5.6 | Parquet, columnar, SQL | C++, Rust, C++ | – | Apache-2.0, MIT, MIT | 63, 218, 44 | – | not built |
| PyMuPDF 1.28.2 | PDF | C (MuPDF) | – | **AGPL-3.0** or commercial | – | – | never |

Other measured candidates are in `outputs/measure.tsv` (xarray 127 members, faker 753, nltk 302, bokeh 1,313, odfpy 35 with a tri-licence that includes GPL and LGPL, pyxlsb and fpdf2 under LGPL-3.0).

### 4. Pure Python runs in today's guest, with five catches (EXECUTED)

Most of the pure set works as it is: pypdf, beautifulsoup4, html5lib through `pd.read_html`, pyyaml, tomli-w, jinja2, charset-normalizer, networkx, mpmath, joblib, attrs, more-itertools, toolz, rich, pygments, markdown-it-py, tqdm, typing-extensions, xmltodict, narwhals, xlrd, odfpy (`pd.read_excel(engine="odf")` round trip). Seven outputs were compared with native and match (`outputs/native-parity.txt`). The catches:

**a. Step 70 drops `.dist-info`, and some packages read their own metadata.** `df.to_markdown()` fails with `InvalidVersion: 'unknown'` (pandas checks tabulate's version, which tabulate reads from its metadata); plotly and altair raise `PackageNotFoundError` at import; `markdown`'s extensions by short name (`extensions=['tables']`) fail because they are entry points. Keeping each wheel's `METADATA` and `entry_points.txt` adds 73 members for the 58 distributions and fixes tabulate and markdown (EXECUTED: `outputs/followup.tsv`). It is a change to `make_stdlib_zip.py`, ours. **It is a prerequisite of the pure set.**

**b. Writing .xlsx with openpyxl needs a writable `/tmp`.** openpyxl writes each worksheet through `tempfile.NamedTemporaryFile`. With the default of nothing writable (§4.15) it fails with "No usable temporary directory"; with `root=True` the pandas round trip passes. xlsxwriter with `{"in_memory": True}`, directly or through `pd.ExcelWriter(..., engine_kwargs=...)`, works with no `/tmp` at all (EXECUTED). So Excel output works in every call that grants a writable folder, and in memory through xlsxwriter otherwise. The README should say so; the default stays.

**c. The `ctypes` stand-in is too thin for two packages.** sympy imports `c_long` and `sizeof` from `ctypes` at import (`sympy/external/gmpy.py:3`, to size a C long); threadpoolctl uses `ctypes.c_uint32` at module level, and scikit-learn imports threadpoolctl. Both fail today (EXECUTED). A wider stand-in (the few type names, `sizeof` giving wasm32's sizes, a `CDLL` that raises `OSError`) is a recipe change; for threadpoolctl a small stand-in module reporting no native thread pools is the cleaner one (INFERRED).

**d. pandas' Styler cannot find its templates in a zip, so `df.style` and `df.to_latex()` fail even with jinja2 present.** pandas builds `jinja2.FileSystemLoader(Path(__file__).parent / "templates")` (`pandas/io/formats/style_render.py:75`), and a path inside a zip is not a folder. The templates are in today's zip (EXECUTED: `unzip -Z1`). jinja2's `PackageLoader` handles a zip (EXECUTED: it resolves `/usr/local/lib/python315.zip`). A one-line carried patch to pandas, with its upstream pull request, would fix it (INFERRED); `df.to_html()` does not use jinja2 and is unaffected (READ).

**e. Resource reads from the zip cost fuel in proportion to its size, and pytz multiplies it.** (EXECUTED: `outputs/resources.tsv`.)

| zip | members | `import zoneinfo` (total, start included) | first `ZoneInfo('Europe/Paris')` | a second zone | `pytz.timezone(...)` (total) |
|---|---|---|---|---|---|
| today's + pytz | 2,362 | 337 M | +649 M | +261 M | 155,299 M |
| with the candidates | 7,360 | 727 M | +1,219 M | +843 M | 500,338 M (500,249 M in `outputs/followup.tsv`) |

A resource read goes through `zipfile.Path`, which parses the zip's directory in Python each time (INFERRED from the slope: about 116,000 fuel per member per read). pytz checks hundreds of zone files by resource on its first lookup, so one `pytz.timezone()` costs 155 G fuel today and 500 G with the larger zip. pytz is unusable from a zip; pandas 3 does not need it, and `zoneinfo` on the zip's tzdata is the working route. The resource cost also touches today's build (every tz-aware pandas call that loads a zone) and grows with every member added (finding 5).

**f. No threads and no network, as documented.** `threading.Thread.start()` raises "can't start new thread"; joblib falls back to serial and returns the same result; tqdm runs. `import socket` works, but `requests.get` fails at `_socket.getaddrinfo` (EXECUTED). Network libraries are dead weight unless a future door-backed client exists (§4.4: that is the tool protocol's business, not a socket).

### 5. What members cost (EXECUTED: `outputs/guest/fuel.tsv`)

- Plain `-c pass`: 241.5 M and 241.9 M with today's 1,751 members; 678.9 M and 678.5 M with 7,360. **77,912 fuel per member** ((678.71 − 241.70) M / 5,609), close to spec 023's review (76,490). With metadata kept: 684.7 M (+73 members, +6.0 M).
- Each resource read: about 116,000 fuel per member (finding 4e).
- The snapshot holds the directory already, so a snapshot call does not pay the per-member start cost (READ: the trim memo, +2.0% with matplotlib's whole set). It does pay each resource read (INFERRED: `zipfile.Path` is built per read).

### 6. Native candidates (READ, sub-agent; Pyodide sizes EXECUTED)

| package | language | what WASI lacks that it touches | prior WASI build | Pyodide `.so` | grade |
|---|---|---|---|---|---|
| regex | C, one file | nothing | wasi-wheels, Pyodide | 0.66 MB | easy |
| bottleneck | C | nothing (templated sources) | Pyodide | 0.17 MB | easy, low value |
| numexpr | C++ | threads unless forced to one; `pthread_sigmask` | none | – | moderate, low value |
| lxml + libxml2 + libxslt | Cython, C | `dup()` in libxml2 (patch or recipe), no iconv, no threads | **boomslang, static wasip1** | 4.71 MB | moderate |
| scikit-learn | Cython, C++ | OpenMP (optional: `required: false` in `sklearn/meson.build:104`, EXECUTED read), threadpoolctl (4c), joblib serial | Pyodide (no OpenMP) | 6.0 MB | moderate, after scipy |
| statsmodels | Cython | scipy's `cython_blas` (`statsmodels/tsa/statespace/meson.build`) | Pyodide | 4.24 MB | moderate, after scipy |
| pydantic-core | Rust (PyO3) | panic=abort; snapshot wraps | **boomslang, static wasip1** | 4.28 MB | Rust |
| orjson, tiktoken | Rust | orjson wants nightly and is part MPL-2.0; tiktoken downloads its BPE files | Pyodide, wasi-wheels | 0.40, 1.68 MB | Rust |
| cryptography | Rust + OpenSSL | OpenSSL cross-build | Pyodide | 6.44 MB | hard |
| pyarrow | C++ | Arrow's thread pool, many libraries | Pyodide (prebuilt) | 43.6 MB | hard |
| duckdb | C++ | threads (can be off), size | duckdb-wasm (Emscripten) | 42.8 MB | hard |
| polars | Rust, huge | rayon, nightly, feature surgery; Pyodide's fork stuck at 1.33 | Pyodide fork | 109 MB | hard |

### 7. Rust extensions can be linked; the costs are elsewhere (EXECUTED and READ, sub-agent)

- rustc's `wasm32-wasip1` is tier 2 with std; its default features equal wasi-sdk 33 clang's (EXECUTED). A Rust `staticlib` linked with the SDK's clang next to standard-EH C++ and wasm setjmp, with and without LTO, and ran (EXECUTED). The staticlib carries no libc of its own; Rust and C share one `malloc`.
- PyO3's CI runs its tests on `wasm32-wasip1` against a static WASI libpython, moved to CPython 3.15 in PyO3 #6340 (READ). boomslang links pydantic-core statically into a wasip1 CPython 3.14 through the inittab, with a one-line shim module (READ).
- **The blockers are not the linker:** (1) panic=abort, so a Rust panic traps the whole guest; unwinding needs nightly `-Zbuild-std`. (2) Rust std calls WASI directly, not through wasi-libc's `__wasi_*` functions that step 60 wraps for the snapshot, so Rust state made before the snapshot would be frozen (EXECUTED: `llvm-nm` shows the direct imports). (3) Pins: a Rust toolchain, its std, and every crate of each `Cargo.lock`; one umbrella crate so the binary holds one std; `crate-type` changed to `staticlib` (a recipe override or a carried patch).
- So Rust is a project of its own: a research memo and a specification for the toolchain and the snapshot wrap, before any Rust package. None is needed for 0.1.0's core.

### 8. Sizes (INFERRED from Pyodide, the scipy memo's 0.92 ratio)

Tier B's native code: 0.92 × (6.0 + 4.24 + 4.71 + 0.66) MB ≈ **14.4 MB** on `python.wasm`, which is about 38 MB after matplotlib M1 (EXECUTED there) and about 58 to 63 MB after scipy (INFERRED there), so about 72 to 77 MB with tier B.

## The tiers

**A. Include: pure Python, high value, small cost.** One pin and one `--wheel` line each, plus a judge job each.

- Files: openpyxl (+et-xmlfile), xlsxwriter, xlrd, pypdf, defusedxml.
- Text and formats: beautifulsoup4 (+soupsieve), html5lib (+webencodings), pyyaml (pure), tomli-w, jinja2 (+markupsafe, pure), tabulate, charset-normalizer (pure), xmltodict.
- Maths and modelling: networkx, sympy (+mpmath), patsy.
- Utilities: attrs, more-itertools, toolz, tqdm, typing-extensions, joblib (+cloudpickle), threadpoolctl (with a stand-in), narwhals.
- After matplotlib M1 (they need it or Pillow): seaborn, reportlab.

**B. Include if built: native and valuable, on the scipy line.**

- scikit-learn (after scipy; no OpenMP; joblib serial; threadpoolctl stand-in). The fourth most used library in both benchmarks and on every hosted list.
- statsmodels (+formulaic, interface-meta, wrapt in its pure form; after scipy).
- lxml with libxml2 and libxslt, which unlocks python-docx and python-pptx (pure, and then tier A) and the faster `pd.read_html` and `pd.read_xml`.
- regex (one C file; nltk and tiktoken need it; cheap).

**C. Later, or a separate profile.**

- Columnar: pyarrow, polars, duckdb (C++ or Rust, 40 to 110 MB each in Pyodide). A "columnar" profile, after the profiles memo is answered.
- Rust: pydantic, orjson, tiktoken, altair (through rpds-py), pdfminer.six and pdfplumber (through cryptography; pdfplumber also needs PDFium). After a Rust toolchain specification.
- plotly: pure, but 1,534 members and 9.7 MB, reads its validators by file path (fails from a zip), and can only write HTML here (static images need kaleido and a browser).
- pytz: unusable from a zip (finding 4e); revisit only if resource reads become cheap.
- numexpr, bottleneck (speed only), xarray, rich, faker, odfpy, scikit-image, shapely and geopandas (GEOS, PROJ), opencv, wordcloud.

**D. Not useful in this sandbox.** requests, httpx, urllib3, aiohttp and their stacks (no network); kaleido (a browser); numba (a JIT); torch and tensorflow; nltk and textblob without their downloaded corpora; tiktoken without its BPE files. PyMuPDF is excluded by its AGPL licence, pyxlsb and fpdf2 by LGPL-3.0 (unless the owner approves those).

## What it costs (EXECUTED members and bytes; INFERRED totals)

At 77,912 fuel per member on a plain start (`outputs/tiers.txt`; reportlab added by hand):

| set | members | deflated zip | plain-start fuel | native code |
|---|---|---|---|---|
| A (with seaborn and reportlab) | 2,258 | 19.4 MB | +176 M | none |
| of which sympy and mpmath | 936 | 9.3 MB | +73 M | none |
| B (Python parts) | 1,330 | 10.0 MB | +104 M | about 14.4 MB |
| A + B | 3,588 | 29.4 MB | **+280 M** | about 14.4 MB |

- 0.1.0's zip would then hold about 6,630 members (1,751 today, matplotlib +681, scipy +610, A + B +3,588): a plain `pass` of about 620 M fuel against 242 M today (2.6 times), and a zone load or any other resource read near 0.8 G each (INFERRED, linear). The snapshot's start does not grow with members.
- Metadata kept for each wheel: about one or two members per distribution more.

## Licences the owner would approve (READ: each wheel's metadata)

Already approved families (§4.12) cover most of these by kind, but §4.12 approves by component, so each is listed.

- **Tier A:** openpyxl, et-xmlfile (MIT); xlsxwriter (BSD-2-Clause); xlrd (BSD); pypdf (BSD-3-Clause); defusedxml (PSF-2.0); beautifulsoup4, soupsieve, html5lib (MIT); webencodings (BSD); pyyaml, tomli-w, tabulate, charset-normalizer, xmltodict (MIT); jinja2, markupsafe (BSD-3-Clause); networkx, sympy, mpmath (BSD-3-Clause); patsy (BSD-2-Clause); attrs, more-itertools, narwhals (MIT); toolz, joblib, cloudpickle, threadpoolctl, seaborn (BSD-3-Clause); typing-extensions (PSF-2.0); reportlab (BSD); **tqdm (MPL-2.0 AND MIT): a new family, file-level copyleft.**
- **Tier B:** scikit-learn, statsmodels, lxml (BSD-3-Clause); formulaic, interface-meta (MIT); wrapt (BSD-2-Clause); libxml2 and libxslt (MIT); python-docx, python-pptx (MIT); **regex (Apache-2.0 AND CNRI-Python): CNRI-Python is a new family.**

## The order of specifications

1. **The zip carries what packages need** (step 70 and recipes): keep `METADATA` and `entry_points.txt`; widen the `ctypes` stand-in; a threadpoolctl stand-in. Small; it is the prerequisite of tier A, and its checks are findings 4a and 4c turned into judge jobs.
2. **The zip's directory is read once:** a research memo first (a placeholder now), on cutting the per-member plain-start cost and the per-read resource cost (findings 4e and 5). It decides whether tier A waits for it (owner's question 2).
3. **Tier A,** after matplotlib M1 lands (both change the build recipe, §5.7): the pins, the `--wheel` lines, the licence notices, one judge job per package (an .xlsx written and read, a PDF's text, `pd.read_html`, `df.to_markdown()`, a template, a graph, a formula). seaborn and reportlab with or after M2.
4. **pandas' Styler from a zip:** one carried patch with its upstream pull request (finding 4d).
5. **scipy** (the roadmap's milestone 3), then **scikit-learn**, then **statsmodels**.
6. **lxml** with libxml2 and libxslt, then python-docx and python-pptx.
7. **regex,** whenever a recipe slot is free.
8. After 0.1.0: a Rust toolchain memo (pydantic first); the columnar profile.

## What it decides

- Tier A is pure Python and needs no new build machinery: only step 70's existing `--wheel` path, once the zip keeps metadata and the `ctypes` stand-in is wider.
- Tier B rides on scipy: scikit-learn and statsmodels are meson-python builds like those already done, without OpenMP or threads; lxml has a proven static-wasip1 recipe to study.
- Rust, Arrow, polars and DuckDB are not 0.1.0 material: each needs its own toolchain work or a profile of its own.
- Network and thread libraries add nothing here.
- The real cost of a bigger profile is the per-member and per-read fuel of zipimport and `zipfile`, not the bytes; it should be measured and cut before the zip triples.

## Questions for the owner

1. **Tier A and tier B as listed, with their licences?** That includes tqdm's MPL-2.0 and regex's CNRI-Python, both new families.
2. **Plain start grows from about 242 M to about 620 M fuel** with matplotlib, scipy, A and B (snapshot calls do not pay it). Accept, or build "the zip's directory is read once" first?
3. **sympy:** on every hosted list but rare in benchmarks; 936 members, 9.3 MB, 73 M fuel on plain start. In the default profile or not?
4. **Excel output with nothing writable:** openpyxl needs `/tmp`; xlsxwriter in memory does not. Document it and keep the default, as this memo recommends?
5. **pytz:** leave it out (agents get `ModuleNotFoundError` and `zoneinfo` works), as this memo recommends?
6. **scikit-learn, statsmodels and lxml in 0.1.0,** after scipy, or in the release after it?

## Where it stopped, and what was not run

- No native candidate was built for `wasm32-wasip1` here; tier B's sizes are inferred from Pyodide's Emscripten wheels.
- seaborn and reportlab were not run (no matplotlib or Pillow in today's artifacts); python-docx and python-pptx not run (no lxml).
- The snapshot was not rebuilt with a larger zip; the claims about snapshot calls are from the trim memo and inference.
- The resource-read cost is a slope from two zips and two zones, not a profile of `zipfile`.
- The ChatGPT list is a community `pip list` from inside the product, not an OpenAI document.

## Sources (READ, web, 2026-10-17)

- Claude API code execution tool, preinstalled libraries: https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
- Gemini code execution, supported libraries: https://ai.google.dev/gemini-api/docs/code-execution
- ChatGPT code interpreter `pip list` (community, 2026-03): https://gist.github.com/hyle/5c240a6343b7d4f3401e27dc75f72420
- OpenAI code interpreter tool: https://developers.openai.com/api/docs/guides/tools-code-interpreter
- AWS Bedrock AgentCore preinstalled libraries: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-preinstalled-libraries.md
- E2B code-interpreter template: https://raw.githubusercontent.com/e2b-dev/code-interpreter/main/template/requirements.txt
- Pyodide 314.0.7 packages: https://pyodide.org/en/stable/usage/packages-in-pyodide.html
- smolagents `BASE_BUILTIN_MODULES`: https://raw.githubusercontent.com/huggingface/smolagents/main/src/smolagents/utils.py
- DS-1000: https://github.com/xlang-ai/DS-1000; BigCodeBench: https://arxiv.org/abs/2406.15877 and the `bigcode/bigcodebench` dataset; "LLMs Love Python": https://arxiv.org/html/2503.17181v1
- rustc `wasm32-wasip1`: https://doc.rust-lang.org/rustc/platform-support/wasm32-wasip1.html
- PyO3 #6340 (wasip1 CI on CPython 3.15): https://github.com/PyO3/pyo3/pull/6340; PyO3 #5239; https://pyo3.rs/main/building-and-distribution
- HubSpot boomslang (Apache-2.0): https://github.com/HubSpot/boomslang
- dicej/wasi-wheels: https://github.com/dicej/wasi-wheels

## One line

Add about thirty pure-Python packages (Excel, PDF, HTML, YAML, templates, graphs, sympy, seaborn) once the zip keeps metadata and a wider `ctypes` stand-in; build scikit-learn, statsmodels, lxml and regex on the scipy line; leave Rust, Arrow, polars, DuckDB, plotly and pytz for later; and cut the zip's per-member fuel before the zip triples.
