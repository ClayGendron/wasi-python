# What data folders the packages need

- **Status:** research, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5). Box: about 75 minutes;
  stopped at about 70. The gaps are listed under "Where it stopped".
- **Feeds:** the matplotlib specification, and the wasi-vfs research
  that `2026-10-16-where-package-data-lives.md` asks for (its C3).
- **Stands on:** `2026-10-16-what-matplotlib-needs.md` (the pins) and
  `2026-10-16-where-package-data-lives.md` (C2: a read-only preopen at
  the path the package already looks in).

## The question

Besides matplotlib's `mpl-data`, which **special folders** do the
shipped and planned packages need at run time?

A special folder is anything a package reads or writes on the
filesystem that `zipimport` cannot serve from inside the stdlib zip.
That means a plain `open()`, `os.listdir`, a C `fopen`, a path handed
to a C library, or any write. `importlib.resources.files(...)` on a
zip works for reads; `open(Path(__file__).parent / ...)` does not.

Scope, by the versions the repository pins or the memos name:
CPython 3.14.8 (the stdlib we ship), numpy 2.5.2, pandas 3.0.6,
python-dateutil 2.9.0.post0, tzdata 2026.5 (all shipped); matplotlib
3.11.2, Pillow 13.0.0, kiwisolver 1.5.1, contourpy 1.4.0, fonttools
4.67.0, cycler 0.12.1, pyparsing 3.3.3, packaging 26.3 (planned); the
stdlib `sqlite3`, `bz2` and `lzma` (planned); scipy 1.18.1, the latest
release on PyPI on 2026-10-16 (planned).

## Method

- **Guest probes (EXECUTED).** Each probe is a short program run on
  the real 0.1.0a1 artifacts in `build/artifacts/` through
  `wasi_python.run(["-c", prog], root=<fresh scratch dir>, env=...,
  fuel=10**12)`, on the snapshot unless the text says "plain". The
  drivers and probe programs are in
  `/private/tmp/claude-501/-Users-claygendron-Git-Repos-wasi-python/7b89cd25-8736-42c1-aab5-0a17add8b573/scratchpad/research-folders/scripts/`
  (`drive.py`, `drive2.py`, `drive3.py`, `p1_env.py` to `p8.py`).
  Every probe exited 0; the failures quoted below are exceptions the
  probe caught and printed.
- **The zip's contents (EXECUTED).** Every non-`.pyc` member of
  `build/artifacts/python-stdlib.zip` was listed with `zipfile`.
- **The binary (EXECUTED).** `strings python.wasm` was searched for
  absolute paths and environment variable names.
- **Sources read (READ).**
  - Shipped: the unpacked trees in `build/` (`numpy-2.5.2`,
    `pandas-3.0.6`, `Python-3.14.8/Lib`) and `scripts/make_stdlib_zip.py`,
    `scripts/steps/70_zip.sh`, `recipes/reactor_bootstrap.py`.
  - Planned: wheels and sdists in the session scratchpad. matplotlib,
    Pillow, kiwisolver and contourpy (sdists hash-checked against the
    matplotlib memo's pins; EXECUTED `shasum -a 256`, all match). New
    downloads, each into its own empty directory, each hash checked
    against PyPI's JSON (EXECUTED, all match):
    ```
    4304f03ed7f4ba000a8dcc941ad854bfa52e2f3b6112b8f099b6f431cf98e701  fonttools-4.67.0-py3-none-any.whl
    85cef7cff222d8644161529808465972e51340599459b8ac3ccbac5a854e0d30  cycler-0.12.1-py3-none-any.whl
    ece8c00a69cf01b45d0b1dedabb469c90d8caf996d4fda40f147627a122849a4  pyparsing-3.3.3-py3-none-any.whl
    d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c  packaging-26.3-py3-none-any.whl
    011413b7426b75012840e35649e00fe0a2c3bae89fed433876e3a99251572efc  scipy-1.18.1-cp314-cp314-macosx_14_0_arm64.whl
    85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67  jinja2-3.1.6-py3-none-any.whl
    2e9ad7dd851bf45fab9f75cbff4cb493fee9979e8d8c7c9c3ee119022518edd6  markupsafe-3.0.4.tar.gz
    0a9c8e34352dad46006aa82836d5383bff9dc6bc9ce5a60553c05aa30e6ad1f9  sqlite-amalgamation-3540100.zip
    ```
    SQLite publishes SHA3-256; the zip's SHA3-256 matched the
    download page's `92281c86…8e30` (EXECUTED). One file,
    `scipy/stats/_sobol.pyx` at tag `v1.18.1`, came from
    `raw.githubusercontent.com` (sha256 `b83490eb…c8fd`), because the
    wheel holds only the compiled module.
  - Each tree was searched with `grep` for `open(`, `__file__`,
    `importlib.resources`, `pkgutil`, `os.environ`/`getenv`,
    `expanduser`/`Path.home`, `XDG_`, `tempfile`, `mmap`, `fileno()`
    and `os.dup`, tests excluded. Hits were read in context.
- Nothing was installed. Downloaded Python ran only as a guest under
  wasmtime (jinja2 and markupsafe, finding 4). Host-side Python that
  read downloaded files ran with `-I`.

## Findings

### 1. The guest's starting state (EXECUTED, `p1_env.py`)

- The guest root holds only `usr/` (the runner's zip). There is no
  `/tmp`, no `/etc`, no `/dev/null`, no home directory.
- `os.environ` is exactly what the embedder passes, `{}` by default.
  The bootstrap replaces it on every call
  (`recipes/reactor_bootstrap.py`, `run`; READ).
- `HOME` unset: `os.path.expanduser("~/x")` returns `'~/x'`, and
  `pathlib.Path.home()` raises `RuntimeError: Could not determine
  home directory.` There is no `pwd` module.
- `sys.path` is `['/usr/local/lib/python314.zip',
  '/usr/local/lib/python3.14', '/usr/local/lib/python3.14/lib-dynload']`.
  The last two are directories inside the guest's writable root
  (see finding 8).
- `sys.flags` show `isolated=1`, `ignore_environment=1`,
  `no_user_site=1`. `ignore_environment` stops CPython's own `PYTHON*`
  start-up variables only. Modules that read `os.environ` themselves
  (zoneinfo's `PYTHONTZPATH`, tempfile's `TMPDIR`, matplotlib's
  `MPLCONFIGDIR`) still see what the embedder passed (EXECUTED in
  finding 2 and 3).
- Not built in: `_sqlite3`, `_bz2`, `_lzma`, `_ssl`, `_hashlib`,
  `_ctypes`, `pwd`, `fcntl`, `_posixsubprocess`. `unicodedata`,
  `zlib`, `_zoneinfo`, `_decimal`, `pyexpat` are built in.
- **The binary hard-codes no data path (EXECUTED).** `strings
  python.wasm` finds `/usr/local` (the prefix) and docstrings, but no
  `/etc/...`, `/usr/share/...` or `/tmp`. wasi-libc's `localtime` is
  UTC only, so no C code reads `/etc/localtime`. Every data path below
  comes from Python code.

### 2. The stdlib we ship

**zoneinfo and tzdata (EXECUTED, `p2_tz.py`, `p5_env.py`, `p6.py`).**
- `zoneinfo.ZoneInfo("America/New_York")` works. The UTC offset on
  2024-07-01 is −4 h. `available_timezones()` returns 598 keys.
- Lookup order (READ, `Lib/zoneinfo/_common.py`, `_tzpath.py`):
  first each directory of `TZPATH`, then the `tzdata` package through
  `importlib.resources.files("tzdata.zoneinfo")`. The second step
  reads from the zip.
- `TZPATH` is the build's config value: `/usr/share/zoneinfo`,
  `/usr/lib/zoneinfo`, `/usr/share/lib/zoneinfo`, `/etc/zoneinfo`.
  All four are paths inside the guest's writable root.
- The data: 605 files, 513,511 bytes (236,619 deflated), IANA 2026e,
  in the zip under `tzdata/`.
- `PYTHONTZPATH` redirects the first step. With `PYTHONTZPATH=` (empty)
  `TZPATH` becomes `()`, and only the zip's `tzdata` is used. The
  bootstrap calls `zoneinfo.reset_tzpath()` when the variable is set,
  so this works on the snapshot too, where zoneinfo is pre-imported.

**time and `TZ` (EXECUTED).** `time.tzname` is `('UTC', 'UTC')`.
`time.tzset` does not exist. Setting `TZ` changes nothing. Local time
is UTC, by the platform. No folder is involved.

**tempfile (EXECUTED, `p3_misc.py`, `p5_env.py`).**
- The candidate list is `['/tmp', '/var/tmp', '/usr/tmp', '/']`. None
  of the first three exists, so `gettempdir()` returns `'/'`, the
  guest root itself.
- `mkstemp()` gave `/tmpu4w9xh0g`, and the file stayed in the root
  after the run. `NamedTemporaryFile` and `TemporaryDirectory` work and
  clean up.
- `TMPDIR=/tmp` with a `tmp/` directory in the root gives `/tmp`. A
  `TMPDIR` that does not exist falls back down the list, silently.
- `importlib.resources.as_file()` on a zip member extracts it to a
  temporary file (EXECUTED: `/tmpo15bsbkeUTC`, read back as `TZif`)
  and removes it after. So any package that uses `as_file` needs a
  writable temp directory.
- `atexit` handlers run at the end of a call (EXECUTED: a directory
  registered for `shutil.rmtree` was gone from the root afterwards).

**mimetypes (EXECUTED).** `guess_type("a.csv")` gives `text/csv` from
the built-in table. `mimetypes.knownfiles` lists `/etc/mime.types` and
eight more paths. They are read if they exist, and all of them are in
the guest root: a planted `/etc/mime.types` changed `guess_type` in
the next run (finding 7).

**locale and gettext (EXECUTED).** `setlocale(LC_ALL, "")` gives
`C.UTF-8`. `setlocale(LC_ALL, "de_DE.UTF-8")` is accepted, but
`localeconv()["decimal_point"]` stays `"."`: wasi-libc has no locale
data. `gettext`'s default directory is `/usr/local/share/locale`, which
does not exist; `translation(..., fallback=True)` works. No catalogs
are shipped and none is needed.

**email (READ).** No data files at run time. The zip carries
`email/architecture.rst`, which nothing reads.

**importlib.metadata (EXECUTED).** `version("numpy")`,
`version("pandas")` and `version("tzdata")` raise
`PackageNotFoundError`; `distributions()` is empty.
`make_stdlib_zip.py` skips every `.dist-info` directory (READ). It
could be served from the zip: `importlib.metadata` reads
`*.dist-info` under any `sys.path` entry, a zip included (INFERRED from
its `zipfile.Path` support). Today's and the planned packages do not
need it: matplotlib's two uses catch `PackageNotFoundError`
(`backends/registry.py:145-151`, `pyplot.py:523-529`; READ).

**`/dev/null` (EXECUTED).** `os.devnull` is `'/dev/null'`, and opening
it raises `FileNotFoundError`. No shipped or planned package opens it
at run time (READ: matplotlib only builds a `Path` from it as a dummy
home, `font_manager.py:136-138`).

**ssl and certifi (EXECUTED: not built).** `_ssl` is absent and the
guest has no sockets. Certificates are out of scope.

### 3. numpy 2.5.2

- **Read-only data: none at run time (READ).** No non-test numpy
  module opens a file relative to `__file__`. The zip carries a few
  stray data files (licences, `numpy.pc`, an f2py meson template),
  which nothing reads at run time.
- `numpy.get_include()` returns
  `/usr/local/lib/python314.zip/numpy/_core/include`, and that
  directory does not exist (EXECUTED): the zip builder skips `.h`
  files. That matters only for compiling extensions, which the sealed
  runtime never does.
- `numpy.f2py` imports but cannot build anything (no compiler, no
  processes).
- **Writable folders: none of its own.** `np.memmap` and
  `np.load(..., mmap_mode="r")` fail with `OSError: mmap is
  unavailable on wasm32-wasi`, from the `recipes/mmap_stub.py`
  stand-in (EXECUTED). That is a documented absence.
- **Broken today: binary file I/O on real files (EXECUTED,
  `p4_npy.py`).**
  - `np.save("/a.npy", np.arange(3))` raises `OSError: [Errno 58] Not
    supported` and leaves a 128-byte file in the root. That is the
    header without the data.
  - `np.load("/a.npy")` of a good file, `ndarray.tofile` and
    `np.fromfile` fail the same way.
  - The cause (READ): when the target is a real file, numpy calls
    `tofile`/`fromfile`, which get a C `FILE*` through
    `npy_PyFile_Dup2`, which calls `os.dup`
    (`numpy/_core/include/numpy/npy_3kcompat.h:96`;
    `numpy/lib/_format_impl.py:764-772`, `:847-849`). WASI preview1 has
    no `dup`: `os.dup(0)` raises the same `Errno 58` (EXECUTED).
  - What still works (EXECUTED): `np.savez_compressed` and `np.load`
    of a `.npz` (they go through `zipfile`), `np.savetxt`/`np.loadtxt`,
    and `np.save` into an `io.BytesIO`.
  - This is not a folder problem, but it breaks the commonest numpy
    file format. `tests/known_gaps.toml` and the README do not mention
    it (READ, `grep`).

### 4. pandas 3.0.6

- **Time zones work (EXECUTED, `p2_tz.py`).** `pd.Timestamp("2024-07-01",
  tz="America/New_York")` gives `-04:00`, its `tz` is a
  `zoneinfo.ZoneInfo`; `tz_convert`, a `date_range` across the DST
  change, `to_datetime(utc=True)` and `tz="dateutil/Europe/London"`
  all give native answers. `pytz` is not shipped and not needed.
  pandas reads no time-zone file of its own (READ: no `__file__` or
  `importlib.resources` use in `pandas/_libs/tslibs`).
- **The Styler templates need a filesystem path (READ, then
  EXECUTED).**
  - The templates are 8 files, 8,852 bytes, under
    `pandas/io/formats/templates/`, and they are in the zip.
  - `StylerRenderer` loads them with
    `jinja2.FileSystemLoader(pathlib.Path(__file__).parent.resolve() /
    "templates")` (`pandas/io/formats/style_render.py:74-76`). A
    `FileSystemLoader` uses plain `open()`, so it cannot read the zip.
  - jinja2 is not shipped: `df.style` raises `AttributeError: The
    '.style' accessor requires jinja2` (EXECUTED).
  - jinja2 alone would not fix it. jinja2 3.1.6 and markupsafe 3.0.4
    (pure Python) were placed in the root's `/usr/local/lib/python3.14/`
    and run on the plain reactor. `import jinja2` worked, and
    `df.style.to_html()` then raised `TemplateNotFound: 'html.tpl' not
    found in search path:
    '/usr/local/lib/python314.zip/pandas/io/formats/templates'`
    (EXECUTED, `p7.py`).
  - `DataFrame.to_html()` (no jinja2) works (EXECUTED).
- **Writable folders: none of its own.** File paths are the user's.
  Verified to work on the guest root (EXECUTED): `to_csv`/`read_csv`
  plain, `.gz` and `.zip`; `to_pickle`, `to_json`, `to_xml(parser=
  "etree")`, `show_versions(as_json=path)`.
- What fails is module absence, not folders (EXECUTED): `.bz2` and
  `.xz` (no `_bz2`/`_lzma`), `to_sql` (no `_sqlite3`), `to_parquet` (no
  pyarrow), `to_clipboard` (no ctypes).

### 5. python-dateutil 2.9.0.post0

- **Its own zone tarball is read from the zip (EXECUTED).**
  `dateutil/zoneinfo/dateutil-zoneinfo.tar.gz` is 156,400 bytes, read
  through `pkgutil.get_data`. `get_zonefile_instance()` holds 598
  zones. Its data is IANA 2024a, older than tzdata's 2026e (EXECUTED,
  `p8.py`). pandas' `tz="dateutil/..."` strings use it.
- **It searches the root first, and has no knob (EXECUTED, READ).**
  `dateutil.tz.tz.TZPATHS` is the same four root paths as zoneinfo's,
  as a module constant. No environment variable changes it.
  `PYTHONTZPATH` does not. A planted zone file is read first
  (finding 7).
- No writable folder.

### 6. matplotlib 3.11.2 and its dependencies (READ unless marked)

**matplotlib: read-only data.** `mpl-data/` holds 204 files, 9.7 MB:
fonts 8,872 KB (`ttf` 7.2 MB, `afm` 824 KB, `pdfcorefonts` 632 KB),
`sample_data` 544 KB, `images` 292 KB, `stylelib` 148 KB,
`matplotlibrc` 48 KB, `kpsewhich.lua` (EXECUTED `du`). Every reader
goes through `get_data_path()`, which is
`Path(__file__).with_name("mpl-data")` (`__init__.py:638-640`).
Readers that run on a headless Agg/SVG/PDF figure:
- `rcParamsDefault` reads `mpl-data/matplotlibrc` at import
  (`__init__.py:993`).
- `style/__init__.py:30,241` globs `mpl-data/stylelib/*.mplstyle` at
  import.
- `FontManager.__init__` lists `mpl-data/fonts/{ttf,afm,pdfcorefonts}`
  (`font_manager.py:1236`). FreeType opens the font files by path.
- `backend_pdf.py:1876`, `backend_ps.py:404` read the AFM directories.
- `_mathtext.py:663` and `ticker.py:658` name `cmsy10.ttf`/`cmr10.ttf`.
- `cbook.get_sample_data` reads `sample_data/` (examples only).

None of these work from the zip. The read-only preopen (C2) at
`/usr/local/lib/python314.zip/matplotlib/mpl-data` serves them all.
Only dotted-package styles use `importlib.resources`
(`style/__init__.py:118`), which works from the zip.

**matplotlib: writable folders.**
- `get_configdir()` and `get_cachedir()` (`__init__.py:528-635`):
  - `MPLCONFIGDIR` first, for both.
  - Else, by `sys.platform`. On `linux`/`freebsd` it is
    `$XDG_CONFIG_HOME`/`$XDG_CACHE_HOME`. Our guest's `sys.platform`
    is `wasi`, so it takes the "other platforms" branch:
    `Path.home() / ".matplotlib"`. The XDG variables are not consulted.
  - With `HOME` unset, `Path.home()` raises `RuntimeError` (EXECUTED,
    finding 1). matplotlib catches it, calls
    `tempfile.mkdtemp(prefix="matplotlib-")`, sets `MPLCONFIGDIR` to it
    in `os.environ`, registers `shutil.rmtree` at exit, and logs a
    WARNING. In our guest that directory lands in the root,
    `/matplotlib-xxxxxxxx` (EXECUTED, the same `mkdtemp` call in
    `p6.py`). The warning goes to stderr through logging's last-resort
    handler (EXECUTED, `p8.py`).
  - So without `MPLCONFIGDIR` or `HOME`, every run warns on stderr,
    rebuilds the font cache, and deletes it at exit (INFERRED from
    the code and the EXECUTED pieces).
- What lives there:
  - `fontlist-v3.11.0.json`, the font cache
    (`font_manager.py:1834-1847`). A `….json.matplotlib-lock` file is
    created next to it while it is written (`cbook._lock_path`,
    `cbook.py:1925-1960`). If a guest is killed while holding the
    lock, the next run on that root retries 50 times with
    `time.sleep(0.1)`, gets `TimeoutError` (an `OSError`), logs
    "Could not save font_manager cache" and goes on (INFERRED).
  - `stylelib/` under the config directory, read at import
    (`style/__init__.py:32,193`).
  - `matplotlibrc` under the config directory, after `./matplotlibrc`
    and `$MATPLOTLIBRC` (`__init__.py:643-684`).
  - `tex.cache/` and `vartexfonts/` (`texmanager.py:65`,
    `dviread.py:1264,1321`), for `usetex` only. That needs TeX
    binaries through `subprocess`, and the guest has no processes
    (EXECUTED: `subprocess.check_output(["fc-list"])` raises `OSError:
    [Errno 58] wasi does not support processes.`).
- **The snapshot freezes these choices (INFERRED).** `get_configdir`
  and `get_cachedir` are cached on first call, and the first call
  happens at import. A snapshot that pre-imports matplotlib keeps the
  directory chosen in `wizer.initialize`; the bootstrap's
  `os.environ` reset does not change it. The matplotlib memo's plan
  (`MPLCONFIGDIR` set in `wizer.initialize`, `pyplot` pre-imported)
  is consistent with this. A pre-imported `fontManager` also means the
  font cache is never read or written at run time.
- **System fonts are searched in the root.** On a non-Windows,
  non-emscripten platform `findSystemFonts()` runs `fc-list` (it fails
  and is caught) and lists `X11FontDirectories`: `/usr/share/fonts/`,
  `/usr/local/share/fonts/`, `$XDG_DATA_HOME/fonts` or
  `~/.local/share/fonts`, `~/.fonts` and two more
  (`font_manager.py:148-162,278-325`). All are inside the guest root.
  `MPL_IGNORE_SYSTEM_FONTS` (any non-empty value) skips all of it
  (`font_manager.py:301-303`).
- Every environment variable matplotlib reads at run time:
  `MPLCONFIGDIR`, `MATPLOTLIBRC`, `MPLBACKEND`,
  `MPL_IGNORE_SYSTEM_FONTS`, `XDG_DATA_HOME`, `SOURCE_DATE_EPOCH`, and
  `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` (Linux only). The others
  (`DISPLAY`, `QT_API`, `LOCALAPPDATA`, `WINDIR`, CI names) belong to
  GUI backends, Windows or tests.

**Pillow 13.0.0.** No data files are shipped (only `py.typed`).
- `ImageFont.load_default()` builds its font from base64 bytes in the
  module (`ImageFont.py:972`, `:1110`). No file is read.
- `ImageFont.truetype("Name.ttf")` with a bare name searches
  `$XDG_DATA_HOME` (else `~/.local/share`) and `$XDG_DATA_DIRS` (else
  `/usr/local/share:/usr/share`) under `fonts/` (`ImageFont.py:900-925`).
  matplotlib does not use this; it passes full paths.
- `ImageFile.load` tries `mmap` for uncompressed images and falls back
  on `OSError` (`ImageFile.py:343-368`), so the stub is harmless.
- `ImageFile._save` writes through `fp.fileno()` with C `write`
  (`ImageFile.py:669`; `src/encode.c`, `write(fh, …)`). There is no
  `dup`, so the numpy break of finding 3 does not apply (INFERRED).
- `tempfile` is used only by `Image.show`, EPS (Ghostscript),
  `ImageGrab` and the external-`cjpeg` path, all of which need
  processes.

**kiwisolver, contourpy, cycler, pyparsing, packaging.** Nothing.
No data files beyond `py.typed`, and no file access at run time
(`grep`). pyparsing reads `PYPARSINGENABLEALLWARNINGS` only.

**fonttools 4.67.0.** Nothing that matplotlib reaches. `fontTools.agl`
keeps its glyph list in the module. The only data file is a README.
`tempfile` appears only in `fontTools.diff` and the UFO temp
filesystem.

### 7. The root is searched first, and a previous run can change answers (EXECUTED)

On one root, run A planted `/usr/share/zoneinfo/America/New_York` (a
copy of `Asia/Tokyo` from tzdata) and `/etc/mime.types`; run B, with an
empty environment, then saw (`p5_plant.py`, `p5_env.py`):

```
ok  NY offset -> datetime.timedelta(seconds=32400)      zoneinfo: Tokyo's +9 h
ok  dateutil NY offset -> datetime.timedelta(0)         dateutil: the planted file
ok  guess .zzz -> ('application/x-planted', None)       mimetypes
```

dateutil's offset is 0 rather than +9 h because it reads only a TZif
file's version-1 block, which tzdata's files leave empty (INFERRED
from the output). With `PYTHONTZPATH=/nowhere`, zoneinfo went back to
`-04:00` and dateutil stayed on the planted file.

This is the shared-root exposure spec 001 already names. It does not
cross the host wall. Its answer is the same: one root per untrusted
program, or calls one at a time on a root the embedder trusts. For
time zones, `PYTHONTZPATH=` (empty) also closes zoneinfo's half.

### 8. The plain reactor imports from the writable root; the snapshot does not (EXECUTED)

`/usr/local/lib/python3.14` is on `sys.path` after the zip. With
jinja2 placed there:

| artifact | `sys.path_importer_cache["/usr/local/lib/python3.14"]` | `import jinja2` |
|---|---|---|
| plain `python.wasm` | `FileFinder('/usr/local/lib/python3.14')` | works, from the root |
| snapshot | `None` | `ModuleNotFoundError` |

The snapshot was taken when the directory did not exist, so its path
cache holds `None` for it (INFERRED from the output). Two consequences:

- On the plain reactor, any module that is not in the zip can be
  supplied by whatever is in the root. That includes the absent
  `_bz2`, `_lzma`, `_sqlite3`, and pandas' optional `pytz`, `jinja2` or
  `pyarrow`. A previous run on a shared root can plant them.
- The two artifacts differ. Neither behaviour is documented
  (`grep` of the specifications and README). It is not a data need,
  but any plan that adds pure packages "beside the zip" must decide it.

### 9. sqlite3, bz2, lzma (planned; READ)

- **bz2 and lzma** need no data and no folder. `Lib/bz2.py`,
  `Lib/lzma.py` and `_compression.py` open only the caller's paths.
- **sqlite3** needs no read-only data. It does need writable
  directories (SQLite 3.54.1 amalgamation, `sqlite3.c`):
  - On `__wasi__`, SQLite defines `SQLITE_WASI`, drops extension
    loading, and defaults to `SQLITE_THREADSAFE=0` (`:11774-11783`).
  - Its default VFS on WASI is `unix-dotfile` (`:40844-40852`). That
    locks a database by creating the directory `<db>.lock` beside it
    (`dotlockLock`, `osMkdir`, `:43097`, `:43167`). Rollback journals
    are `<db>-journal`, also beside it. So the directory that holds a
    database must be writable.
  - WAL's shared-memory index is compiled out on WASI
    (`#if !defined(SQLITE_WASI) && !defined(SQLITE_OMIT_WAL)`,
    `:42489` and after).
  - Temporary files (large sorts, temp tables, `VACUUM`) go to the
    first writable directory of: `sqlite3_temp_directory`,
    `$SQLITE_TMPDIR`, `$TMPDIR`, `/var/tmp`, `/usr/tmp`, `/tmp`, `.`
    (`unixTempFileDir`, `:46918-46945`). In today's guest that is `.`,
    the root (INFERRED). Python's `os.environ` writes call `putenv`, so
    the C `getenv` sees the embedder's values (INFERRED).
  - Compiling with `SQLITE_TEMP_STORE=3` keeps temporary tables in
    memory (INFERRED, from SQLite's documented compile option; not
    traced in the source here).
  - A guest killed while holding a lock leaves `<db>.lock` behind. The
    next run on that root gets "database is locked" until it is
    removed (INFERRED from the dotfile design).

### 10. scipy 1.18.1 (planned; READ)

- **Read-only data, by the wheel's listing (EXECUTED):** outside the
  tests, one data file is read at run time:
  `scipy/stats/_sobol_direction_numbers.npz`, 589,334 bytes. The rest
  are licences, the qhull and DUCC sources' notes, and 680 test files
  that the zip builder would skip.
- **The Sobol table works from the zip, with a temp file.**
  `_initialize_direction_numbers` uses
  `importlib.resources.files("scipy.stats")` and then
  `importlib.resources.as_file(...)` before `np.load(f)`
  (`_sobol.pyx:147-150`). From a zip, `as_file` writes the 589 KB to
  `tempfile.gettempdir()` and removes it after (EXECUTED for a tzdata
  member, finding 2). `np.load` of an `.npz` goes through `zipfile`,
  not `fromfile`, so the `dup` break does not hit it (INFERRED). Cost:
  a 589 KB write and read on each run that creates a `Sobol` engine.
- **`scipy.datasets`** downloads through pooch into
  `pooch.os_cache("scipy-data")`, which is `$XDG_CACHE_HOME` or
  `~/.cache/scipy-data` (`datasets/_fetchers.py:14-25`;
  `datasets/__init__.py:64`). pooch is not planned, and the guest has
  no network. Out of scope, as the constitution's "no network" says.
- **Other file readers.** `scipy.io.wavfile` (`wavfile.py:516`) and
  `scipy.io.FortranFile` (`_fortran.py:270`) call `np.fromfile` on
  real files.
  They would hit finding 3's `dup` failure (INFERRED). `scipy.io`'s
  netcdf reader uses `mmap.mmap(fp.fileno(), …)` (`_netcdf.py:271`).
- Environment variables at run time: `SCIPY_ARRAY_API`,
  `SCIPY_DEVICE`. No config or cache directory besides pooch's.

### The table

"Zip" means `zipimport` or `importlib.resources` serves it today or
would if shipped. "FS" means it needs a real path.

| package | read-only data (size; from zip?) | writable folders (env var to redirect) | works today / needs what |
|---|---|---|---|
| zoneinfo + tzdata 2026.5 | 605 files, 513,511 B; **zip, works** (E) | none. It searches `/usr/share/zoneinfo` and 3 more in the root first (`PYTHONTZPATH`; empty = zip only) | **works** (E) |
| time | none; UTC only, `TZ` ignored | none | works, UTC only (E) |
| tempfile | none | `/tmp`, `/var/tmp`, `/usr/tmp`, else **`/`** (`TMPDIR`) | works; litters the root without `TMPDIR` (E) |
| mimetypes | `/etc/mime.types` and 8 more, optional; built-in table | none | works (E) |
| locale, gettext | `/usr/local/share/locale`, optional; none shipped | none | works, C locale data only (E) |
| importlib.metadata | `*.dist-info`, stripped from the zip; zip would serve it | none | `PackageNotFoundError` for all (E); no package here needs it |
| `os.path.expanduser`, `Path.home` | none | `HOME` | `~` unexpanded; `Path.home()` raises without `HOME` (E) |
| ssl, certifi | out of scope | — | `_ssl` not built (E) |
| numpy 2.5.2 | none at run time; headers stripped (`get_include()` dangles) | none | **`np.save`/`np.load` of `.npy`, `tofile`, `fromfile` on files fail: no `dup`** (E); `.npz`, text, `BytesIO` work |
| pandas 3.0.6 | Styler templates: 8 files, 8,852 B; **FS** (`FileSystemLoader`), in the zip but unreadable | none of its own | tz, CSV, pickle, JSON work (E); Styler needs jinja2 + markupsafe **and** an FS path (E) |
| python-dateutil 2.9.0.post0 | zone tarball 156,400 B (IANA 2024a); **zip, works** (E) | none. Root `TZPATHS` searched first, **no knob** | works (E) |
| matplotlib 3.11.2 | `mpl-data/`, 204 files, 9.7 MB; **FS** | config + cache dir (`MPLCONFIGDIR`; else `$HOME/.matplotlib`; else a `mkdtemp` in the root plus a warning); system fonts in the root (`MPL_IGNORE_SYSTEM_FONTS`) | not built; C2 preopen + `MPLCONFIGDIR` + `MPL_IGNORE_SYSTEM_FONTS` |
| Pillow 13.0.0 | none; default font is in the code | none for matplotlib's use; font-by-name search in `XDG_DATA_HOME`/`XDG_DATA_DIRS` | not built; no folder needed |
| kiwisolver, contourpy, cycler, pyparsing, packaging | none | none | not built; no folder needed |
| fonttools 4.67.0 | none (glyph list in code) | none on matplotlib's path | not built; no folder needed |
| bz2, lzma | none | none (caller's paths) | `_bz2`, `_lzma` not built (E) |
| sqlite3 (SQLite 3.54.1) | none | the database's directory (journal, `<db>.lock`); temp dir (`SQLITE_TMPDIR`, `TMPDIR`, else `.`) | `_sqlite3` not built (E); `unix-dotfile` default on WASI |
| scipy 1.18.1 | `_sobol_direction_numbers.npz` 589,334 B; **zip, via `as_file`** (needs a temp dir) | temp dir for `as_file` (`TMPDIR`); pooch cache (`XDG_CACHE_HOME`) for `datasets` | not built; `datasets` needs network (out); `scipy.io` readers hit the `dup` break |

(E) = EXECUTED on 0.1.0a1. Everything else in the table is READ, from
the findings above, unless a finding marks it INFERRED.

## What it decides

The needs fall into four groups.

**(a) Served from the zip already, or would be if shipped.**
- tzdata, through `importlib.resources` (zoneinfo).
- dateutil's zone tarball, through `pkgutil.get_data`.
- scipy's Sobol table, through `importlib.resources.as_file`. That
  needs a writable temp directory: group (c).
- matplotlib's dotted-package styles, fonttools' glyph list, and
  Pillow's default font. These are in code or reached through
  `importlib.resources`.
- `*.dist-info`, if the zip builder kept it. No package here needs it.

**(b) Read-only data that needs a real filesystem path.** These are
the candidates for a read-only preopen (C2 of the package-data memo)
or for wasi-vfs (its C3).
- **matplotlib `mpl-data/`**: 204 files, 9.7 MB. Needed by every
  figure.
- **pandas' Styler templates**: 8 files, 8.8 KB. Needed only if jinja2
  and markupsafe are ever shipped. Under C2 it would be a second data
  preopen at `/usr/local/lib/python314.zip/pandas/io/formats/templates`.
- **One preopen cannot cover both (INFERRED).** A preopen named
  `/usr/local/lib/python314.zip` would win the longest-prefix match
  for the zip's own path. The zip would then resolve to a directory,
  and `zipimport` would break. So C2 means one preopen per data
  directory. wasi-vfs would take any number of directories into one
  image. That is a point for the wasi-vfs experiment.
- Nothing else in scope needs this group. numpy's headers and f2py's
  sources are not needed at run time. The tests' data are not
  shipped.

**(c) Writable folders the embedder can point into the guest's root
by environment variable alone.** Each one was honoured in a probe or
read in the source. None needs a recipe.
- `TMPDIR`, for tempfile, `importlib.resources.as_file` (scipy) and
  SQLite's temporary files (also `SQLITE_TMPDIR`). The directory must
  exist. Without it the root `/` is used (EXECUTED).
- `MPLCONFIGDIR`, for matplotlib's config and cache (font cache,
  user styles, `matplotlibrc`). On `wasi`, matplotlib ignores the XDG
  variables. Without `MPLCONFIGDIR` it falls back to `HOME`, then to a
  temp directory with a warning on every run. Under a snapshot, the
  value is frozen at build time (INFERRED).
- `HOME`, for `expanduser` and `Path.home()`. matplotlib's fallback
  also uses it.
- `XDG_CACHE_HOME` for pooch, and `XDG_DATA_HOME`/`XDG_DATA_DIRS` for
  Pillow's font search by name. Neither is on the planned paths.
- Read-side knobs in the same style: `PYTHONTZPATH=` (empty) makes
  zoneinfo use only the zip, and `MPL_IGNORE_SYSTEM_FONTS=1` stops
  matplotlib from scanning font directories in the root. Both close a
  shared-root channel (finding 7). dateutil's `TZPATHS` has no such
  knob.
- SQLite's journal and lock directory are not redirectable: they sit
  beside the database file, which is the caller's choice.

**(d) Blockers.**
- **numpy binary file I/O is broken in 0.1.0a1 (EXECUTED).**
  `np.save`/`np.load` of `.npy` on a real file, `tofile` and `fromfile`
  fail with `Errno 58`, because numpy calls `os.dup` and WASI preview1
  has none. `np.save` also leaves a truncated file. The same path
  would break `scipy.io.wavfile` and `FortranFile` (INFERRED). The fix is not a folder. It is either a documented gap
  with the `io.BytesIO` workaround, or an upstream numpy change to
  fall back to Python-level writes when `dup` fails. Either way it
  needs a check and a `known_gaps` entry first. Patching numpy, or
  faking `os.dup`, is not allowed (constitution §4.1, §4.11).
- **pandas Styler.** It needs jinja2 and markupsafe in the zip **and**
  group (b) for its templates. Without both it stays a documented
  absence.
- **scipy.datasets** needs the network. Out of scope.
- **matplotlib `usetex`, animation writers, `fc-list`** need
  processes. Out of scope on WASI.
- No blocker was found for the matplotlib smallest set beyond what the
  two earlier memos already list.

**For the matplotlib specification:**
1. The runner (and the README's embedder steps) should pass
   `MPLCONFIGDIR` to a directory in the root and
   `MPL_IGNORE_SYSTEM_FONTS=1` when matplotlib ships. Under the
   snapshot plan, both should also be set in `wizer.initialize`.
2. A check should assert there is no "Matplotlib created a temporary
   cache directory" warning on stderr, so a lost `MPLCONFIGDIR` shows
   up as a failure.

**For the runner, independent of matplotlib (owner's call):**
1. Create `/tmp` in the root and pass `TMPDIR=/tmp`, so temp files stop
   landing in `/`.
2. Pass `PYTHONTZPATH=` (empty) by default.
3. Decide finding 8: whether the plain reactor should keep
   `/usr/local/lib/python3.14` on `sys.path`.

Each of these is a runner default, not a recipe or a patch.

## Where it stopped

- No planned package was built, so their findings are READ or
  INFERRED. The two strongest INFERRED claims need a build to
  confirm: the snapshot freezing matplotlib's config directory, and
  scipy's Sobol `as_file` path working from the zip.
- SQLite was read, not built. `SQLITE_TEMP_STORE` was not traced in
  the source. Whether CPython's `_sqlite3` builds against the
  `unix-dotfile` default unchanged was not tested.
- The cause of finding 8 (`None` in the snapshot's path importer
  cache) is inferred from the output. The CPython path-hook code was
  not read.
- No Windows run.

## One line

Besides `mpl-data`, the only read-only data that needs a real path is
pandas' Styler templates. Every writable need (temp files,
matplotlib's cache, SQLite's temp files) can be pointed into the
guest's root by `TMPDIR`, `MPLCONFIGDIR` and `HOME`. The real surprise
is a bug, not a folder: in 0.1.0a1, `np.save` and `np.load` of `.npy`
files fail because WASI has no `dup`.
