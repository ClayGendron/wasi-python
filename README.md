# wasi_python

**A statically linked CPython for WebAssembly hosts, with numpy, pandas and
matplotlib compiled in. No browser, no JavaScript. A few pinned releases, not every
version of everything.**

One `python.wasm` for `wasm32-wasip1` that runs on a WASI host with
WebAssembly exception handling (see *Hosts*), from your own Rust, Go or
Python program. The packages are linked in as builtin modules, so there is
no `dlopen`, no shared library and no package install step inside the
guest. The sandbox is WASI's capability model: the guest sees only the
directories and host functions you hand it.

- Site: <https://wasipython.dev>
- Status: **alpha.** `0.1.0a1` (CPython 3.14.8, wasi-sdk 24) is a GitHub
  pre-release; the next alpha moves to CPython 3.15.0 and wasi-sdk 33.
- Licence: Apache-2.0.

## What you get

| artifact | what it is |
|---|---|
| `python.wasm` | a WASI reactor: CPython plus numpy, pandas, matplotlib's compiled modules (with FreeType, HarfBuzz, SheenBidi and libraqm), Pillow's core, kiwisolver, lxml's `etree` and `objectify` (with libxml2 and libxslt), zlib, bz2, lzma, sqlite3, the `host` door; `_initialize`, then one `run` per instance |
| `python-snapshot.wasm` | the same binary after a Wizer snapshot with numpy and pandas pre-imported; one `run` per instance, about 20 ms |
| `python-stdlib.zip` | the stdlib plus numpy, pandas, matplotlib (its data as one inner archive), Pillow, kiwisolver, lxml, fontTools, cycler, pyparsing, packaging, python-dateutil, tzdata, six, and `host`, the tool protocol's guest package, as a deflated zip |
| `MANIFEST`, `SHA256SUMS` | every pinned source, every supported build host's toolchain, and every recipe hash |

Published as GitHub release assets (xz, 6 to 22 MB) and as the `wasi-python`
wheel on PyPI, which carries the same files and a `wasi_python.artifacts()`
function that returns their paths.

## Measured (arm64 macOS, wasmtime 49)

Times are from the first scripted build on the 3.14 line (spec 003's landing
notes, 2026-10-16); sizes and instruction counts are the 3.15 line's (spec 005's
landing notes, 2026-10-17). Times are benchmark facts on one machine, not
promises.

| fact | value |
|---|---|
| upstream patches | upstream patches carried: 6, each with an upstream pull request drafted for the owner to send, or, for matplotlib's, already merged upstream (`recipes/patches/`); every other adaptation is a recipe file |
| build from pinned sources, downloads present | 8 min 35 s (macOS arm64, 10 cores, with matplotlib's and lxml's steps; spec 046's landing notes, 2026-10-18) |
| `python.wasm` / `python-snapshot.wasm` / `python-stdlib.zip` | 40.4 MB / 74.4 MB / 22.1 MB (3.15 line, with matplotlib and lxml; spec 046's landing notes) |
| `import numpy` | `origin == 'built-in'`, no `.so` opened |
| one call, snapshot, `-c pass` | 20 ms, of which about 14 ms is finalizing the interpreter; 83.4M guest instructions on 3.15 with matplotlib (81.9M before) |
| one call, snapshot, skipping finalization (`os._exit(0)`; flush first) | 6 ms |
| one call, plain reactor, `-c pass` / `import pandas` | 21 ms / 620 ms (spec 035's landing notes, 2026-10-18: the zip's directory read once); 167M / 4.92G guest instructions with matplotlib's members in the zip (151M / 4.90G before; spec 023) |
| a line plot saved as PNG, snapshot, matplotlib not pre-imported | 7.56G guest instructions with a fresh font cache (a fresh `HOME`), 5.57G with a kept `MPLCONFIGDIR` (spec 023) |
| numpy kernels vs native (the spike's measurement) | 1.6 to 2.3 times slower (no SIMD, no BLAS, no threads) |
| pandas groupby, 1e6 rows, vs native (the spike's) | 1.3 to 1.4 times slower |
| numpy, pandas, bz2, lzma and sqlite3 results vs native, same pins | byte-identical on six golden jobs |
| numpy's and pandas' own tests in the guest (spec 050; upstream's fast selection, 11 groups) | 63,717 passing; 12 gaps, each a class of known failures listed by node id with its closer (the README 10, question 89 2); no test traps the guest |

The platform's facts, documented rather than patched (with six carried patches,
below and under *matplotlib in the guest* and *lxml in the guest*), are what `python.wasm -V` prints after its version:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl or zstd; compute about 1.3 to 2.3 times slower than native)

So `np.arange(1_000_000).sum()` wraps (use `dtype=np.int64`). A C++
`throw` inside a package (numpy's FFT, for one) is caught as in native
code and reaches Python as an exception. A script's directory is not put on `sys.path`: the interpreter
runs isolated. `np.save` and `np.load` of paths and open files work, through a
carried patch (`recipes/patches/numpy-2.5.2/`) until numpy releases the fix;
`ndarray.tofile` and `np.fromfile` on real files still fail, since WASI cannot
duplicate a descriptor (use `tobytes()` and `np.frombuffer`, or `io.BytesIO`), and
memory maps are unavailable. `np.save` of a masked array to a path raises
`NotImplementedError`, as natively. A truncated `.npy` file read from a path raises the
`ValueError` numpy gives for in-memory streams ("EOF: reading array data, …"), not native's
"Failed to read all data for array"; the type is the same. A second carried patch gives six of
numpy's C callbacks the signatures CPython calls them with, so `copy.copy` of a numpy scalar and
`a.dtype = …` work instead of trapping the guest; the judge scans every build's callback tables
for that class of mistake. Tracebacks and warnings name a module in the zip by its full zip path,
`/usr/local/lib/python315.zip/pandas/core/frame.py`, as native zip imports do, so pandas'
warnings point at the caller's line. There is no `/dev/null`: `os.devnull` names a path that
does not exist, so opening it raises `FileNotFoundError`. The stdlib zip carries no package's
`tests` folders and no `conftest.py`, so `numpy.conftest`, which numpy's own module list names,
does not import. `importlib.metadata` gives each package's name, version and entry
points; `files()` gives `None`, because the zip keeps no `RECORD`. The zip's directory is read
once per process, by the reactor's own reader, and resource reads and metadata answer from that
one read (spec 035): a first time zone costs about 9 M fuel on the snapshot, a metadata lookup
that finds nothing about 11 M, and `version("numpy")` about 0.15 G, most of it parsing
`METADATA`. `importlib.resources.files()` on a package in a zip on `sys.path` gives the runtime's
own `Traversable`, `ZipDirectoryPath`, not a `zipfile.Path`: the same bytes, listings, `is_file`,
`is_dir`, `exists`, `name`, `parent`, `str()` and errors, and `zipfile` itself reads any member
that is not stored or deflated, is over 1 MiB, or fails a check, and any member opened with a
`pwd` (so a guest's own zip keeps `zipfile`'s CRC checks, LZMA, passwords and streaming). It
lacks `zipfile.Path`'s `root`, `at`, `filename`, `glob`, `rglob`, `match`, `relative_to` and
`is_symlink`; names with `//` or a leading `/` list zipimport's implied folders, not zipfile's; a
duplicated name lists once and an empty name not at all; and two `files()` calls give equal
paths. Resources and metadata also see a zip as zipimport last read it, as its imports do: a zip
on `sys.path` that a program rewrites in place keeps its old listing and its old distributions
until `importlib.invalidate_caches()`, so a new member is not found, and a distribution whose
`METADATA` moved raises `MetadataNotFound` (a `FileNotFoundError`, not a
`PackageNotFoundError`). The bytes read are always the zip's current ones: a stale entry fails
the member reader's checks, and `zipfile` reads it. `import ctypes`
works: it sizes wasm32's C types and gives numpy their dtypes, but it loads no library and calls
nothing; each such use raises `OSError`, as a missing library does, which is why `-V` still says
"no ctypes". So does asking numpy or pandas for the dtype of a `Structure`, `Union`, pointer,
array or function type (the stand-in computes no layouts), and with it `inspect.getmembers` and
`hasattr(t, "__numpy_dtype__")` on such a type; `help()` and `dir()` work. The snapshot runs only beside the exact stdlib zip it was built
against (its `MANIFEST` names the zip's hash), because zipimport's file
offsets are part of the snapshot.

`run` treats its arguments as CPython's command line does for one program:
`-c`, `-m`, a script, or `-` and no argument for stdin; `-u`; `-V`. Its return
value is the exit status, masked to 0 to 255 as a POSIX process's is. Output is
buffered as CPython's is without `-u`, so a program that ends in `os._exit` or
is stopped by fuel loses what it printed since its last flush; run it with
`-u`, or flush first. The snapshot adds three facts of its own:

- its string hash secret is fixed (`sys.flags.hash_randomization == 0`), so
  every snapshot instance hashes strings alike;
- the modules it pre-imports were imported with an empty environment: `run`
  re-reads what is known to matter (the `random` and numpy seeds, `logging`'s
  start time, `zoneinfo`'s `PYTHONTZPATH`), and anything else a module read
  from the environment at import keeps the build's value;
- it is the same bytes on every build, from any supported build host: while
  it initializes, the clocks, entropy and file metadata (a directory's size
  and link count included) answer constants, and no program ever sees them.

### sqlite3 in the guest

`sqlite3`, `bz2` and `lzma` are built in. `bz2`, `lzma` and `tarfile`'s
`bz2` and `xz` modes write the same bytes as native Python. `sqlite3` has
native's feature set (FTS3/4/5, R-tree, Geopoly, math functions, dbstat,
percentile) and gives native's results, except two kinds. SQLite's math
functions follow the guest's C library, so their last digits can differ:
over 199 inputs each, the trigonometric and hyperbolic functions, `atan2`,
`log10` and one-argument `log` did, and `exp`, `ln` and `sqrt` did not.
And what changed between SQLite releases (native's is 3.53.1) shows, such
as JSON's float text. WASI has no file locks, so SQLite uses its own WASI default,
and these facts follow from it:

- one connection holds the database, through a `<db>.lock` directory beside
  it, while it writes or has a statement open (an unfinished `SELECT`
  included); a second connection, even in the same program, then gets
  "database is locked" after its busy timeout (5 s by default);
- `journal_mode=wal` silently stays `delete`, unless the connection first
  sets `locking_mode=exclusive`;
- a guest stopped inside a transaction (killed, out of fuel, past its
  deadline, or by a hard exit such as `os._exit`) leaves `<db>.lock` and a hot journal; in a
  reused root the embedder removes the lock directory, and SQLite then rolls
  the journal back; a call with `root=True` never sees a stale lock, since
  its root is fresh (with no root, the default, a database file can live only
  in a writable grant);
- SQLite's own randomness (`random()`, `randomblob()`, its temporary file
  names) is seeded from the time in whole seconds, because the guest has no
  `/dev/urandom` (the process id is always 1 on WASI): two calls in the same
  second repeat it, and a `/dev/urandom` planted in a reused root sets it;
  use `secrets`, `uuid.uuid4()` or `os.urandom` for IDs, which use real
  entropy;
- a database in a read-only directory opens only through a URI that takes
  no lock (`uri=True`), such as `file:<path>?immutable=1` or
  `file:<path>?nolock=1`, because the lock is a directory made beside it;
  `mode=ro` alone is not enough;
- no `load_extension`; `sqlite3.threadsafety` is 0 (native: 3);
- `sysconfig` reports `_bz2` and `_lzma` as missing, `_sqlite3` as
  disabled and `PY_SQLITE_HAVE_SERIALIZE` as 0, because they are linked in
  through `Setup.local`, which CPython's `configure` never sees; all three
  import, and `Connection.serialize` works;
- `shelve` and `dbm` now create `dbm.sqlite3` files, as native does, so a
  shelf holds the lock directory too.

Temporary data goes to files under `TMPDIR` (`/tmp` by default in `run`).

### matplotlib in the guest

matplotlib 3.11.2 is built in, on the Agg backend (spec 023):

```python
done = run(["-c", "import matplotlib; matplotlib.use('agg'); import matplotlib.pyplot as plt;"
            " plt.plot([1, 3, 2]); plt.savefig('/out/plot.png')"],
           grants=[Grant("/tmp/job-17", "/out", writable=True)],
           env={"MPLCONFIGDIR": "/out/.matplotlib"})  # a writable folder for its font cache
```

A line plot's pixels are native matplotlib's at the same pins (FreeType 2.14.3, HarfBuzz
14.1.0, the judge's golden job). The PNG file's bytes are not native's: native Pillow deflates
with zlib-ng, the guest's with zlib, so equal pixels make a different file. PNG, PDF, PS, EPS and
SVG save; Pillow is built with zlib only, so JPEG and the other codecs raise `OSError`; only the
non-interactive backends are in the zip. A Delaunay `Triangulation(x, y)` raises `ImportError`
for `matplotlib._qhull` (explicit triangles work) and `contour` raises `ModuleNotFoundError` for
`contourpy`: both are matplotlib's next milestone. Five more facts follow from the sandbox:

- **matplotlib's data** (`mpl-data`: fonts, `matplotlibrc`, styles) travels in the stdlib zip as
  one member, `matplotlib/mpl-data.zip`. `run` extracts it once per process into its private
  folder, beside its copy of the zip, checks every file as it writes it, compares the whole tree
  with its record before every call (and extracts it again on any difference), and grants it
  read-only at `/usr/local/lib/python315.zip/matplotlib/mpl-data`, the path matplotlib computes.
  Every process pays that extraction at its first call, plotting or not (about 200 files, 9.7
  MB). An embedder without `run` extracts and preopens it itself (see *Running it*).
- **The font cache.** matplotlib writes its font list to `MPLCONFIGDIR`, else `$HOME/.matplotlib`.
  `run` makes `HOME` fresh on every call, so each call that imports matplotlib rebuilds the list
  (about 2 G guest instructions); the snapshot does not pre-import matplotlib. To keep the cache
  between calls, set `MPLCONFIGDIR` (`env=`) to a writable grant you keep.
- **A shared, writable `MPLCONFIGDIR` is trusted by later calls**: its JSON names font files, so
  one call can make the next parse a font of its choosing. Share one only between calls you trust
  alike.
- **No writable `/tmp`, no matplotlib**: with no root and no writable grant at `/tmp` (the default
  since 0.1.0a3) and no `MPLCONFIGDIR`, `import matplotlib` raises `OSError` ("Matplotlib requires
  access to a writable cache directory"). Give the call `root=True`, a writable grant at `/tmp`,
  or `MPLCONFIGDIR` in a writable grant.
- **No threads**: starting one (a `threading.Timer`, say) raises `RuntimeError`; matplotlib's
  drawing and saving never start one.

FreeType's licence asks every binary distribution to say this in its documentation, and this
README is the wheel's description:

> Portions of this software are copyright © 2026 The FreeType Project (https://freetype.org).
> All rights reserved.

### lxml in the guest

lxml 6.1.3 is built in (spec 046): `lxml.etree` and `lxml.objectify` are builtin modules over
libxml2 2.15.4 and libxslt 1.1.45 with libexslt, and lxml's Python package (`lxml.html`,
`lxml.builder`, `lxml.sax`, `ElementInclude`) is in the zip. XPath, XSLT, XInclude, C14N, DTD,
XML Schema, RELAX NG and Schematron validation, the HTML parser and `iterparse` give native
lxml's answers at the same pins (the judge's golden job `lxml_xml`). Files are read and written
by path inside a grant. pandas' `read_html` with no `flavor` uses lxml, and `read_xml` and
`to_xml` use it by default. Native lxml's wheels carry an older libxml2 (2.14.6), so two
outputs differ from them: XSLT's `method="html"` writes `<meta charset="UTF-8">` (2.15's form),
and error messages may name other columns.

**XSLT reads and writes files by default.** A stylesheet given no `access_control` may load
documents (`document()`, `xsl:include`, `xsl:import`) and write them (`exsl:document`), and
libxslt loads each document it reads with its own parse options, which resolve external
entities whatever lxml's parser says. So **an untrusted stylesheet, or an untrusted document a
stylesheet loads, can read any file in a grant, external entities included, and write into any
writable grant.** Give untrusted stylesheets, and trusted ones that load untrusted documents,
`etree.XSLT(sheet, access_control=etree.XSLTAccessControl.DENY_ALL)` (or `read_file=False`,
`write_file=False`): the read or write then raises "read rights … denied" or "write rights …
denied". pandas' `read_xml(…, stylesheet=…)` applies its stylesheet with no access control. The
sandbox keeps all of this inside the grants (no network, nothing outside a grant, nothing
written to a read-only one), but does not make untrusted input safe to transform; libxml2's own
README advises against untrusted input too. lxml's parser keeps its safe defaults: external
entities are not resolved, there is no network, DTDs are not loaded, and entity expansion is
capped.

**Character encodings are wasi-libc's**, not GNU libiconv's (which native wheels bundle; it is
LGPL). Measured over each encoding's whole repertoire in the Basic Multilingual Plane, one
element per character, with `etree`'s XML parser:

| encoding | parse | write |
|---|---|---|
| windows-1252, ISO-8859-2, ISO-8859-15, cp1251, KOI8-R, TIS-620, UTF-16 | every character | every character, native's bytes |
| Shift_JIS | 3 of 6,944 read as another character | the same 3 |
| ISO-2022-JP | 1 of 6,881 read as another character | the same 1 |
| GB2312 | 2 of 7,445 read as another character | `LookupError` |
| GBK, cp949 | every character | `LookupError` |
| EUC-KR | as native (8,226 of the 17,048 characters Python encodes) | `LookupError` |
| cp932 | the document fails ("Invalid bytes": NEC row 13 and IBM extensions) | 460 characters differ |
| EUC-JP | the document fails (JIS X 0212 characters) | 6,069 characters differ |
| Big5, cp950 | the document fails, as natively | `LookupError` |
| GB18030 | the document fails at its first non-ASCII byte ("Invalid bytes"), on purpose | `LookupError` |

The characters read as others are mapping conventions, not damage: Shift_JIS `5C` and `7E` read
as `\` and `~` (native: `¥` and `‾`), Shift_JIS `81 5F` and ISO-2022-JP's fullwidth reverse
solidus as `\`, GB2312 `A1 AA` and `A1 A4` as `—` (U+2014) and `·` (U+00B7) (native: U+2015 and
U+30FB).

**In HTML and in recover mode, a document that fails does not raise: its text ends there.**
libxml2's HTML parser (`lxml.html`, `etree.HTML`, pandas' `read_html`) and
`XMLParser(recover=True)` recover from invalid bytes instead of raising: they keep the text up to
the first character the conversion cannot read, drop the rest, and write
`ERR_INVALID_ENCODING` in the parser's `error_log`. A cp932 page holding `表計算①②ⅰ` reads as
`表計算` in `lxml.html` and in `read_html`, with no exception (native: all of it). So with the
"document fails" rows, check `parser.error_log`, or decode with Python first (below).

**GB18030 fails on purpose.** wasi-libc decodes 1,617 of its characters as other characters
without an error. So its decoder is wrapped (`recipes/iconv_refusals.c`, until a wasi-sdk carries
musl's fix): a GB18030 decode passes ASCII through and fails at the first byte above it. In no
mode is a character read wrongly:

- strict XML (`etree.fromstring`, `etree.parse`) raises `XMLSyntaxError` ("Invalid bytes in
  character encoding");
- `XMLParser(recover=True)` gives no root (`fromstring` returns `None`) and logs
  `ERR_INVALID_ENCODING`;
- the HTML parser keeps only the ASCII text before the first Chinese character, as above (a
  page whose `<title>` is ASCII keeps its title; the body's text after the first non-ASCII byte
  is gone);
- `pd.read_html` finds no table with lxml, then tries `bs4`, which is not in the build, and
  raises `ImportError` (a table entirely before the first non-ASCII byte would still be read);
- naming GB18030 to lxml (`XMLParser(encoding="gb18030")`, `read_html(…, encoding="gb18030")`,
  `tostring(…, encoding="gb18030")`) raises `LookupError`.

Refusing the encoding outright would have been worse: the HTML parser and recover mode then fall
back to windows-1252 and read every Chinese character wrongly, silently.

**The working route** for GB18030 and every partial row is Python's own codecs, which are
complete (CPython's `gb18030` codec among them): decode the bytes in Python and give lxml the
text. To read XML, `etree.fromstring(data.decode("gb18030").encode("utf-8"),
etree.XMLParser(encoding="utf-8"))`, or parse a `str` with no encoding declaration; to read
HTML, `lxml.html.document_fromstring(data.decode("gb18030"))`, or
`pd.read_html(io.StringIO(data.decode("gb18030")))`. To write, serialize with
`encoding="unicode"` and encode the `str` with Python.

Left out, or different, on purpose:

- **`lxml.isoschematron`** reads its stylesheets by file path, which fails from the zip, and their
  licence terms are not approved: `import lxml.isoschematron` raises `ImportError`. libxml2's own
  Schematron, `etree.Schematron`, works.
- **No zlib in libxml2**: `XMLParser(decompress=True)` on a gzip file raises `XMLSyntaxError`;
  decompress with Python's `gzip` first. Writing compressed (`write(…, compression=6)`) works:
  lxml compresses through Python's `gzip`.
- **Catalogs**: libxml2's default catalog is `/etc/xml/catalog`, read only if the embedder grants
  a folder at `/etc/xml` (or sets `XML_CATALOG_FILES` in the guest's environment).
- **Not shipped**: `cssselect` and `lxml_html_clean`, so `lxml.cssselect` and `lxml.html.clean`
  raise lxml's own `ImportError`, as natively without them.
- lxml's `LICENSES.txt` (in `LICENSES/lxml.txt`) describes its wheels, which bundle GNU libiconv
  and zlib; this build links neither.

## Hosts

The binaries use WebAssembly's exception-handling proposal in its standard
form (`exnref`, part of WebAssembly 3.0), so C++ exceptions work; a host
without it cannot load them. They also need multi-value and reference
types (WebAssembly 2.0). Only wasmtime 49 is run by this project; the rest
of the list is read from each runtime's release notes and source
(`context/research/2026-10-16-cpp-exceptions-and-wasi-hosts.md`):

- **runs by default:** wasmtime 47 or later (CLI, Rust, wasmtime-py; 37 to
  46 with `-W exceptions=y`); WasmEdge 0.16 or later (AOT 0.18 or later);
- **runs with a switch:** wasmer 6 or later on LLVM, V8 or Cranelift 7 or
  later (not Singlepass); wazero 1.12 or later with its experimental
  opt-in; Node 24.15 or later, or 25;
- **does not run:** WAMR, wasmi, wasmer-python, wasmer-go, wasmtime's
  Winch, and wasmtime built without its `gc` feature.

For a host without exception handling, use `0.1.0a1` (CPython 3.14.8,
wasi-sdk 24): the `v0.1.0a1` release's assets, or `wasi-python==0.1.0a1`
once that version is on PyPI. On it a C++ `throw` ends the guest, and
matplotlib will never be built for it. C++ cannot be done on WASI without
the proposal under this project's rules (the memo above), so a 3.15 set
without it is not built unless an embedder needs one.

## How it is built

One command, from pinned inputs; the source trees are their tarballs plus the
recorded patches (`recipes/patches/`: six today, numpy's `.npy` fix and its callback
signatures, matplotlib's enum fix from upstream, Pillow's and kiwisolver's callback
signatures, and libxml2's file input without `dup()`):

```
scripts/00_download.sh   # fetch every pin and verify it against downloads/SHA256SUMS
scripts/build.sh         # a preflight, fifteen steps with one line each, a summary; logs in build/logs/
```

`scripts/build.sh` first runs a preflight: the build host's key, the host tools
on `PATH` (`cc make shasum tar gzip xz sed uv git stty df`), and on a first
build at least 2.5 GiB free under `build/`. It prints one line,
`preflight: <host>; 11 tools; <n> GiB free`, or one `ERROR preflight:` line and
stops. Each step then prints one line, `ok <step>: <what it made> [<time>]`.
A failing step prints `FAILED <step>`, the last 20 lines of its log, and last
one line, `ERROR <step>: <reason> (log: …)`, whose reason is the log's last
line starting `ERROR`; so `grep '^ERROR'` gives exactly the reason. A passing
build ends with `done:`, the three artifacts with their sizes and the start of
their hashes, and the next command. Every run adds its steps' times to
`build/logs/timings.tsv`; nothing reads it but the build's own display.

On a terminal one status line sits below those lines and is redrawn in place:
the step, its place in the run, its time against last time, ninja's `[n/N]`
for numpy and pandas, and the time left. When the build ends, the terminal shows
exactly what a pipe or CI log shows, apart from colour (`NO_COLOR` turns it
off). A pipe, `CI`, `TERM=dumb` or `--plain` gives the plain lines only.

```
scripts/build.sh --list        # each step, what it does, and its last time
scripts/build.sh --from 60     # that step and every later one
scripts/build.sh --resume      # the step the last run did not finish, and every later one
scripts/build.sh 60 70         # only the named steps
scripts/build.sh --check       # the preflight alone
```

Nothing is skipped on its own: each step removes and remakes its outputs.
Ctrl-C stops the running step at once and exits 130. A `kill -TERM` or `HUP`
sent to `build.sh` alone waits for the running step to end, because a shell
handles a signal only once its foreground command returns; to stop at once,
signal the process group (`kill -TERM -<pgid>`), as Ctrl-C does.

The steps (`scripts/steps/`): unpack the toolchain and a pinned host Python
(CPython 3.15.0 from python-build-standalone) and install the build tools from
hashed wheels, offline; build CPython with its own `Platforms/WASI` driver;
build zlib, numpy and pandas outside their source trees, cross-compiling with
meson, and the C libraries behind `bz2`, `lzma` and `sqlite3` (bzip2, liblzma
from xz with xz's own `configure`, and SQLite's one-file amalgamation); build libxml2
and libxslt with their own `configure`s and compile lxml's two modules from the C its sdist
ships; link everything into one interpreter as builtin modules and relink it
as a WASI reactor; build the bytecode-only, deterministic stdlib zip; snapshot
the reactor with the pinned wasmtime's own `wasmtime wizer`, numpy and pandas
pre-imported; assemble
`build/artifacts/` with `MANIFEST`, `SHA256SUMS` and the licence notices of
everything inside. The compiler wrapper `scripts/wasi-cc` turns every
extension module's shared link into a static archive, so no `meson.build`
changes. The line's versions (CPython, wasi-sdk, the host Python) are named
once, in `scripts/line.conf`.

**The same bytes from any build host.** The build runs on arm64 macOS, arm64
Linux and x86_64 Linux, and all three give the same artifact set, byte for
byte: the same `SHA256SUMS` over the three artifacts, `MANIFEST` and the
licences (`context/specifications/012-the-same-bytes-from-any-host.md`,
`context/specifications/040-x86-64-rebuilds-the-same-bytes.md`). Every host
compiles with its own pinned wasi-sdk clang, and every compile carries
`-ffp-contract=off`, which step 10 writes into the toolchain's own
configuration files (`bin/clang.cfg`, `bin/clang++.cfg`), read by every
`clang` and `clang++` call whatever the caller
(`context/specifications/059-the-x86-64-rebuild-runs-natively.md`). So the
flag appears in no recorded flag: `sysconfig.get_config_var('CFLAGS')` inside
the guest does not show it, and a rebuild must not add it to a command line.
The judge refuses, on any compiler command in the recipe or in a build's
records, any option that would override the file (`-ffp-model=`,
`-ffast-math`, `-Ofast`, `-funsafe-math-optimizations`, `--no-default-config`,
`--config`, any other `-ffp-contract=`), greps the source trees for a pragma
that turns contraction on, and probes the compiler's own `-cc1` line. Why:
wasi-sdk's x86_64 and aarch64 builds of the same clang order two stack slots of
one `long double` expression differently when the IR holds `llvm.fmuladd`, the
intrinsic clang emits for `a*b+c` under its default contraction setting, so the
x86_64 `python.wasm` differed by 21 bytes
(`context/research/2026-10-17-x86-64-rebuilds-differ-in-one-function.md`,
`context/research/2026-10-18-byte-identical-wasm-builds-prior-art.md`). wasm32
has no fused multiply-add, so run-time arithmetic does not change; a constant
the compiler folds moves by one rounding, to the value the run time computes.
The issue is drafted for LLVM (`context/upstream/4-llvm-wasm-isel-slot-order/`).
Spec 040's emulated compiler stays in the tree, switched off, as the fallback
until the first alpha whose native x86_64 rebuild passed has shipped: one line
in `scripts/line.conf` turns it on. It is the launcher `scripts/clang-emulated`
running the arm64 Linux wasi-sdk's clang under a pinned `qemu-aarch64`, with
five Debian packages pinned by `snapshot.debian.org` URL and hash and fetched
only when the switch names them: `qemu-user` (GPL-2.0), and the aarch64 `libc6`
(LGPL-2.1), `libstdc++6` and `libgcc-s1` (GPL-3.0 with the GCC runtime
exception) and `libtinfo6` (X11) that the clang loads. They are build tools,
like the runner's `cc`: nothing of them is linked into or shipped with an
artifact. Each host's
own inputs (wasi-sdk, wasmtime, the host Python, the Cython and ninja wheels,
and the SDK whose clang compiles there)
are named once per host in `scripts/line.conf` and fetched by that host's
branch of `scripts/00_download.sh`; every host's pins are in
`downloads/SHA256SUMS`. So `MANIFEST`'s `pin` lines name every supported build
host's inputs, not only the ones one build used (its line
`x-pins every-supported-build-host` says so), and `MANIFEST` is the same file
from every host. Four things make the bytes host-neutral: the host's wasi-sdk
keeps only its compiler, and every host links wasi-sdk's host-neutral sysroot
and builtins; the build sorts in the C locale; the snapshot sees a directory's
size and link count as constants; and the stdlib zip's `_sysconfigdata` and
numpy's `__config__.py` say nothing about the build machine. Inside the guest,
`sysconfig.get_config_var('BUILD_GNU_TYPE')` and `numpy.show_config()`'s build
machine therefore say `build`, not the host that built it. No compiler runs in
a WASI guest, so nothing reads them.

The recipe files under `recipes/`: two meson cross files, three rename headers
for symbols that only collide in a static link, the reactor entry, two frozen modules the reactor
links in (`_zip_directory`, which reads the zip's directory with one read where zipimport makes a
dozen Python calls per member, and `_zip_resources`, which answers resource reads and metadata
from that read; each hands anything odd to upstream's own code), the door
module, a host-side numpy stand-in for pandas' build, a one-function stand-in for `mmap` that pandas
imports unconditionally, and a stand-in `ctypes` package (`recipes/ctypes_stand_in/`), which numpy
and pandas import too: it names and sizes wasm32's C types, gives numpy the dtype it gives a real
one, and refuses every foreign call. The stdlib zip also carries each package's `METADATA` (and a
wheel's `entry_points.txt`): a wheel's own, and numpy's and pandas' from their pinned sdists'
`PKG-INFO`.

One host input is not pinned: the native C compiler and `make` that CPython's
driver uses to build its own build-Python. Nothing it compiles is linked into
the guest, and Apple clang and gcc 14.2 give the same artifact bytes
(`context/research/2026-10-16-reproducible-builds-on-linux.md`). The build
also runs host tools that move or check bytes and are not pinned either:
`curl` (only for a pin not yet in `downloads/`), `shasum` (perl's), `tar`,
`xz`, `sed`, `uv` (it installs the pinned wheels, offline, by hash) and `git`
(it lists the recipes for `MANIFEST`). The
release workflow prints each runner's versions of them. xz's own `configure`,
which configures liblzma, also runs the host's shell tools (`sh`, `sed`,
`grep`, `awk`); the same-bytes gate is what shows they leave the artifacts
alone.

**Building on a Mac with Finder open.** Finder writes `.DS_Store` files into
folders you browse, at any moment. Every shell step removes its old outputs
through `remove` (`scripts/steps/remove.sh`), and step 90 through its own
`_remove`; both retry. The zip, the licences
and the artifact set never pack such a file (spec 018). One case is left: a
`.DS_Store` written into the finished `build/artifacts/` makes the judge's
`SHA256SUMS` check fail, naming the file, because a wheel built from that
folder would carry it. Delete it with `find build/artifacts -name .DS_Store -delete`.

## Releasing

Releases are alpha builds for now, numbered `0.1.0aN`. The version lives in one place,
`src/wasi_python/__init__.py`, and `release/version.py` changes it:

```
uv run python release/version.py bump            # 0.1.0a1 -> 0.1.0a2, and a CHANGELOG.md section
uv run python release/version.py release --push  # date the section, tag v0.1.0a2, push: the release runs
```

Pushing the tag starts `.github/workflows/release.yml`. It builds from the pins on arm64 macOS,
checks that the source trees are their tarballs plus the recorded patches, runs the whole judge, and checks the same bytes on Linux, Windows and
macOS. Beside the build, two jobs, `rebuild-linux-arm64` and `rebuild-linux-x86-64`, rebuild the
set from the pins on an arm64 Linux runner and an x86_64 Linux runner, and `same-bytes` requires
each one's `SHA256SUMS` and wheel to equal the set's, byte for byte; nothing is signed or
published until it passes. They are two jobs, not a matrix, so each hands on only its own files'
ids. Each job compiles with its own host's pinned clang (spec 059), so no compiler input is
shared between the two votes, and each job has two hours. Then it publishes
a GitHub pre-release with the wheel, the artifact set as `.tar.xz`, and
their `SHA256SUMS`, and uploads the wheel to PyPI as `wasi-python` through its trusted publisher (from 0.1.0a3). A manual run of
the workflow is a dry run that never publishes (`context/specifications/004-alpha-releases.md`).

Before publishing, an `attest` job signs build provenance for every asset and verifies it
strictly (`context/specifications/009-release-security.md`). If it fails, nothing is published:
re-run the failed jobs of the same workflow run (its artifacts are kept 90 days); never push the
tag again. Dry runs never sign, since a signature is permanent in Sigstore's public log.

Every job that checks, signs or publishes uses exactly the bytes the build job made
(`context/specifications/057-the-release-ties-what-it-signs-to-what-it-built.md`). The build job
hands on its upload's artifact id and the SHA-256 of its `SHA256SUMS`, and prints both, with
`SHA256SUMS`, in its log. Each later job refuses an empty id (an empty one would download every
artifact of the run), downloads by that id, checks `SHA256SUMS` against the hash, every file
against `SHA256SUMS`, and that nothing else is there, and only then acts. `publish` runs in the
`release` environment and `pypi` in `pypi`; their rules are the owner's settings. `setup-uv`'s
cache is off in every job, and each job holds only the permissions it uses. If a re-run of the
failed jobs ever stops at a guard ("handed on no artifact id"), re-run all jobs: the build makes
the same bytes again. After publishing, whoever cut the release compares the GitHub release's
assets (`gh release download`, then `shasum -a 256 -c`) and PyPI's wheel digest with the
`SHA256SUMS` in the build job's log, and records it in the release's notes.

Every action is pinned by a full commit. A pin can name a commit that exists only in a fork, so
when an action is bumped, check that the commit is the named release's tag
(`gh api repos/<owner>/<repo>/git/ref/tags/<version>`).

## Verifying a download

From the first release after `0.1.0a1` (which has no attestation), every release asset carries
build provenance signed by this repository's release workflow at the release's tag:

```
gh attestation verify <asset> --repo ClayGendron/wasi_python \
  --signer-workflow ClayGendron/wasi_python/.github/workflows/release.yml@refs/tags/v<version> \
  --source-ref refs/tags/v<version> --deny-self-hosted-runners
```

`--signer-workflow` matches a prefix of the signer's identity, so it carries the `@` and the
tag, which pins the workflow file exactly. `gh` must be logged in for this. Without `gh`, check
the asset against the release's `SHA256SUMS`.

## Running it

Install it with `pip install wasi-python` (or `uv add wasi-python`). That
brings wasmtime-py (`wasmtime>=49,<50`), which runs the guest. From Python it
is then one call:

```python
from wasi_python import run

done = run(["-c", "import pandas as pd; print(pd.Series([1, 2, 3]).sum())"])
done.exit_code, done.stdout        # (0, b'6\n')
```

`pip install "wasi-python[run]"`, the 0.1.0a3 instruction, still works: the
`run` extra is kept, empty, for compatibility. An embedder that brings its own
wasmtime binding (another version, or another language's host) installs with
`pip install --no-deps wasi-python` and uses `wasi_python.artifacts()` for the
files; importing `wasi_python` never loads wasmtime, only `run` does. Such an embedder
preopens the stdlib zip read-only at `/usr/local/lib`, in a folder holding nothing else, and,
for matplotlib, extracts the zip's member `matplotlib/mpl-data.zip` (an archive of plain files)
into a folder of its own and preopens it read-only at
`/usr/local/lib/python315.zip/matplotlib/mpl-data`.

By default the guest has nothing writable: no `/`, no `/tmp` and no
`HOME`, only the read-only stdlib and whatever the embedder grants (since
0.1.0a3; the owner's rule, constitution §4.15). It can import, compute,
print, read the stdlib and call the door; `open('x', 'w')`, `tempfile`,
`np.save` or `df.to_csv('x.csv')` fail with `OSError`. `root=True` gives the
call a fresh private directory as its `/`, writable, removed afterwards
(what a call got by default before 0.1.0a3); `root=` a path gives it that host
directory instead, writable, at `/`. `grants=` hands it host folders, each
read-only unless it says otherwise (see *Grants*). The stdlib zip is never in a root: every call sees it read-only
at `/usr/local/lib`, and matplotlib's data read-only at
`/usr/local/lib/python315.zip/matplotlib/mpl-data` (see *matplotlib in the guest*). `run` also takes `env`, `stdin`, `host` (a function from
request bytes to response bytes, bound to the door), `snapshot` (the
default; `False` runs the plain reactor), `fuel` (a cap on executed
instructions), `deadline_s`, `memory_bytes`, `output_bytes`, `cache_dir`,
`artifacts`, `cancel` (a `threading.Event`: once it is set, the guest
stops, `trapped` is `"cancelled"`; see *From async code* for how soon), and
`tools`, `gate`, `max_tool_calls` and `max_tool_request_bytes` (see *Tools*). It
returns `exit_code`, `stdout`, `stderr`, `trapped` (`"out of fuel"`,
`"deadline"`, `"cancelled"`, a trap's kind such as `"stack overflow"`,
`"unreachable"` or `"memory out of bounds"`, or, for an error with no trap
code, its first line), `fuel_used`,
`truncated` (the streams whose output hit the cap), and `tools` (a call's
tool record, or `None`). `fuel_used` counts the
guest's own instructions from the end of instantiation, so it is the same
whether the module was compiled or loaded from the `.cwasm` cache (measured
on macOS; Linux maps the memory image itself and never charged for it, and
Windows, which always copies it, is expected to match)
(`context/research/2026-10-17-fuel-depends-on-how-the-module-was-made.md`).

The compiled module is cached as a `.cwasm` in the user cache directory, or
in `$WASI_PYTHON_CACHE`, only where no other user can write (a `.cwasm` is
native code); `cache_dir=False` keeps it in memory only. On Windows the
runner cannot check who may write a folder, so `cache_dir` and
`$WASI_PYTHON_CACHE` must name a folder only you can write; the default, in
your own profile, is one. Measured on Apple
arm64 (spec 001's landing notes): the first call compiles for about 3 s, a
first call with the `.cwasm` on disk takes about 0.1 s, and later calls in
one process about 20 to 25 ms. The runner finds the artifact set through
`wasi_python.artifacts()`: `$WASI_PYTHON_ARTIFACTS`, else a source
checkout's `build/artifacts/`, else the wheel's own copy.

### Grants

```python
from pathlib import Path

from wasi_python import Grant, run

data = Path.home() / "project" / "data"
done = run(
    ["-c", "import os; open('/out/n.txt', 'w').write(str(len(os.listdir('/data'))))"],
    grants=[Grant(data, "/data"), Grant("/tmp/job-17", "/out", writable=True)],
)
```

`Grant(host, guest, *, writable=False)` gives the guest the host folder `host`
at the guest path `guest`, read-only unless `writable=True`. A read-only grant
refuses every write-type call with `EPERM` (`PermissionError` in Python). Grants
may be nested (`/data` read-only with `/data/out` writable), in any order: the
guest's C library picks the longest matching guest path. `HOME` is made fresh
in the folder the guest sees at `/tmp`: a writable grant there, else the root's
own `tmp`; with neither, there is no `HOME`. With no root (the default) there
is no `/`, and a relative path fails.

State that must outlive a call (an agent's notes between turns, say) lives in
a writable grant the embedder keeps: each call reads it at the start and
writes it at the end.

```python
state = Path.home() / "agent-17"  # the embedder's folder for this agent
state.mkdir(exist_ok=True)
run(["-c", "import json, os; p = '/state/n.json'; n = json.load(open(p)) if os.path.exists(p) else 0;"
     " json.dump(n + 1, open(p, 'w')); print(n + 1)"],
    grants=[Grant(state, "/state", writable=True)])
```

Every grant, and `root`, is checked before the guest is set up, and refused
with `TypeError` or `ValueError` (the runner may first make its own module
cache, so that it is judged as it will be):

- a guest path must be absolute, with no empty, `.` or `..` part and no
  trailing `/`; not `/` (that is `root`), not `/usr/local/lib` or under it
  (the runtime's), and no two grants may share one;
- a host path is walked one folder at a time and never through a link in a
  folder you can write, which a guest could have made (on Windows, never
  through any link, junction or other reparse point, which includes
  OneDrive's cloud folders and some container layers); a folder you may
  search but not list is walked through, as wasmtime opens it; a grant's
  folder must exist, and a missing `root` is made. Run as the superuser,
  every folder counts as writable, so every link on the way is refused
  (macOS's `/tmp` and `/var` included): name the real path;
- a read-only grant inside a writable one, or `root`, is refused: the guest
  could change it through the other;
- a writable grant or `root` at, inside or above the runtime's own folders
  is refused, since later calls and processes trust them: the stdlib folder
  (or the temporary folder that holds it), the artifact set, the module
  cache, the code of `wasi_python` and wasmtime-py themselves, and the host
  Python's own `stdlib`, `site-packages` (the user's too) and `bin` (or
  `Scripts`) folders. So
  `root=Path.home()`, a project folder holding the `.venv` this process runs
  from or `build/artifacts`, and the temporary folder itself are refused;
- any grant, read-only too, at or above the temporary folder is refused: it
  holds every call's private folders and `stdin`;
- folders are compared by identity (device and inode), never by spelling.

After wasmtime opens each folder itself, the runner checks, before the guest
runs, that it opened the folder it checked; a folder swapped in between
raises `RuntimeError`. A folder removed between the check and wasmtime's own
open raises wasmtime's `WasmtimeError`. The runner's own preparation of a
`root` (its `usr/local/lib` and `tmp`) goes through the folder it checked,
never its path, so a folder swapped above it changes nothing elsewhere.

What grants do not do:

- `..` never crosses from one grant into another, and a grant does not appear
  in a listing of its parent;
- a read-only grant can still change if the same host files are writable
  elsewhere, by another call or another program;
- a writable grant answers as the host's file system does: on Windows see
  *On Windows* under *Writable mounts*;
- a SQLite database in a read-only grant opens only through a URI that takes
  no lock (`file:/data/db.sqlite?immutable=1`);
- a folder reachable by two routes (a bind mount, a share mounted twice) is
  judged by the route you give. Each route is checked against the runtime's
  files and the other grants by identity, which a bind mount shares and a
  second mount of a network share may not.

#### The import path

```python
lib = Path.home() / "agent-lib"  # holds helpers.py, and tools.zip with a package toolbox
done = run(
    ["-c", "import helpers, toolbox; print(helpers.VERSION)"],
    grants=[Grant(lib, "/lib")],
    import_path=["/lib", "/lib/tools.zip"],
)
```

`import_path=` names guest paths the program may import from; on the command
line, `--import-path GUEST` (repeatable). They go on `sys.path` after the
stdlib zip, in the order given. Each entry is a folder or a zip file inside a
**read-only grant**, and the runner refuses, before any work:

- an entry the root, a writable grant or a mount serves (the guest resolves a
  path by its longest guest prefix, and so does the check), or that nothing
  serves. A mount never serves the import path: one provider can be mounted
  read-only and writable at once, and a later call would import what an
  earlier one wrote through the writable mount;
- a writable grant, or any mount, whose guest path lies under an entry;
- a writable grant, or `root`, whose host folder lies inside the folder of
  the grant serving an entry: the whole grant, not just the entry's
  subfolder (a link inside a grant reaches any folder of it);
- a relative path, `/`, `/usr/local/lib` or under it, or the same entry twice.

The runner does not look for the entry: a missing one, or a file that is not
a zip, is skipped, as Python skips a bad `PYTHONPATH` entry. No `.pyc` is ever
written (not even when a program sets `sys.dont_write_bytecode = False`: the
refused write is quiet), and a valid `.pyc` already in an entry, made for
CPython 3.15, is used.

Entries come after the runtime, so a module the runtime has (the stdlib's,
numpy's, pandas', the tool protocol's `host`) is always the runtime's, on both
binaries: name your packages apart. But a module the runtime looks for and
lacks is taken from an entry: C accelerators (`_decimal`, `_uuid`, `_hashlib`),
other platforms' modules (`nt`, `msvcrt`, `fcntl`, `pwd`, `termios`), and the
profile's optional dependencies (`pytz`, `pyarrow`, `numexpr`, `bottleneck`).
On the plain binary that also happens for packages the snapshot imported when
it was built: an entry's `pytz.py` is imported by `import pandas` on the plain
binary, not on the snapshot. Ship such a name only on purpose.

The runner puts the entries on `sys.path` with a one-line `-c` prelude before
your argv, which then runs your program exactly as before, with two
differences: a program that walks its own stack sees two more frames, so it
reaches the recursion limit two frames sooner (996 frames of its own instead
of 998); and a call with an import path costs more fuel, about 3.5 M on the
snapshot and about 1 M (0.5 to 2 M) on the plain binary. A call without one is
unchanged.

What the runner cannot see is yours to keep apart. Across calls: granting a
folder writable in one call and importing from it in another runs whatever
the first call left there. Within one call, two routes it judges by folder
only: a hard link between a file in an entry's grant and a file in a writable
grant (a write to one is a write to the other), and a writable mount whose
provider stores into an entry's folder. Either lets one call plant code that a
later call imports.

### Mounts

A mount serves a guest's files from your own code: a database, an object
store, a permission layer. The guest opens, reads, lists and stats them with
ordinary calls (`open`, `os.listdir`, `os.stat`, `pandas.read_csv`); your
provider answers each one. Mounts are read-only unless you say
`writable=True` (see *Writable mounts* below).

```python
from wasi_python import Errno, Mount, Stat, run

class Files:  # paths are absolute within the mount: "/" is the mount itself
    def __init__(self, tree):  # {"/a.csv": b"...", "/d": None (a folder)}
        self.tree = tree

    def stat(self, path):
        if path == "/" or self.tree.get(path, b"") is None:
            return Stat("dir")
        return Stat("file", len(self.tree[path])) if path in self.tree else Errno.ENOENT

    def list(self, path):
        prefix = path.rstrip("/") + "/"
        return [(p[len(prefix):], "dir" if v is None else "file")
                for p, v in self.tree.items()
                if p.startswith(prefix) and "/" not in p[len(prefix):]]

    def read(self, path):  # the whole file
        if path == "/" or self.tree.get(path, b"") is None:
            return Errno.EISDIR
        return self.tree.get(path, Errno.ENOENT)

done = run(["-c", "import pandas; print(pandas.read_csv('/work/a.csv'))"],
           mounts=[Mount(Files({"/a.csv": b"x,y\n1,2\n"}), "/work")])
done.files.calls  # {'stat': 0, 'list': 0, 'read': 1, 'write': 0, 'mkdir': 0, ...}
```

**The protocol.** A provider has three methods, each given a normalized
absolute path (`/` is the mount itself) and each answering a value or an
`Errno`, or raising an `OSError` (below):

- `stat(path)` → `Stat(kind, size=0, mtime_ns=0)`, where `kind` is `"file"`
  or `"dir"` (a `Stat` for `/` must be a folder);
- `list(path)` → an iterable of `(name, kind)` pairs, a name being one path
  component (not empty, `.` or `..`, no `/` or NUL, at most 255 bytes of
  UTF-8, no repeats);
- `read(path)` → the whole file as `bytes`, `bytearray` or `memoryview`;
  `Errno.EISDIR` when the path itself is a folder, and `Errno.ENOTDIR` when a
  parent is a file. The runner makes a folder descriptor only from `EISDIR`.

**A path is a name, not a host path.** "Normalized" means `.`, `..` and
repeated `/` are resolved; `/` is the only separator. A component may hold
any character but `/` and NUL, `\` and `:` included, and may be a Windows
device name such as `CON` or `NUL`: the provider gets it as the guest wrote
it, as a Linux grant would. A provider that maps paths onto a host folder
must not join them blindly. On Windows `/..\..\secret` climbs out of the
base and `/C:\Windows` replaces it. Refuse `\`, `:` and device names, or
resolve the joined path and check that it stays inside the base:

```python
target = (base / path.lstrip("/")).resolve()
if not target.is_relative_to(base.resolve()):
    return Errno.EACCES
```

`Errno` holds WASI preview1's own numbers (`EACCES`, `EBUSY`, `ECANCELED`,
`EDQUOT`, `EEXIST`, `EFBIG`, `EINVAL`, `EIO`, `EISDIR`, `ENAMETOOLONG`,
`ENOENT`, `ENOSPC`, `ENOSYS`, `ENOTDIR`, `ENOTEMPTY`, `ENOTSUP`, `EPERM`,
`EROFS`, `ESTALE`, `ETIMEDOUT`, `EXDEV`); the guest sees each as the `OSError`
of that `errno`. The runner knows nothing about permissions: it calls your
provider for every access and passes its answer through. Any other exception,
or an answer outside the protocol, gives the guest `EIO` and adds a `FileFault`
to `done.files.faults`; the run goes on. A `BaseException` that is not an
`Exception` (Ctrl-C, `SystemExit`) stops the call and is raised from `run`, as
a door host's is.

**Raising an OSError.** A method may raise an `OSError` instead of returning
an `Errno`, and the guest gets the same answer. Its errno is matched by name,
never by number, which differs between hosts: `errno.ENOENT` on macOS, Linux
or Windows is `Errno.ENOENT` (44), not WASI's 2. With no errno at all, as in
`raise FileNotFoundError(path)`, the class answers: `FileNotFoundError`,
`FileExistsError`, `IsADirectoryError`, `NotADirectoryError`,
`PermissionError` and `TimeoutError` are `ENOENT`, `EEXIST`, `EISDIR`,
`ENOTDIR`, `EACCES` and `ETIMEDOUT`. An errno outside the set above is `EIO`
and a fault, whatever the class: `EINTR` would make the guest's `open` retry
until a limit stops the run, and `EAGAIN` would tell it to try a whole-file
read again. This holds where your method's own code runs: the call, and
iterating the listing `list` returns (a generator's body). An `OSError` from an
answer object (a `Stat` property, a buffer) is a fault. The guest never sees
the exception's message, only its own C library's text for the errno. A
mapped raise leaves no fault in the record: it is an answer, so a bug in your
provider that raises `FileNotFoundError` reads as the guest's missing file.
Log your raises in the provider if you want to see them. A provider over a
host folder on Windows still answers `EISDIR` for a folder itself: Windows
raises `PermissionError` for `open()` of a folder, which becomes `EACCES`.

At most one provider call per open: an open makes one `read` (or one `list`
with `O_DIRECTORY`, as `os.listdir` and `os.scandir` do), `os.stat` one
`stat`, and `os.fstat` of an open file none. Nothing is cached between opens;
your provider may cache.

**Where.** `Mount(provider, guest)` takes any guest path a grant may use, and
`/`: a mount at `/` makes your provider the guest's whole filesystem, except
what more specific preopens own (the stdlib zip at `/usr/local/lib`, every
grant, every other mount); relative paths then reach it. A mount at `/` is
refused with `root=`. Mounts and grants nest either way, and no two share a
guest path. The runner adds nothing to your listings (list `/usr` yourself if
you want it seen) and makes no `HOME` in a mount: a mount at `/tmp` means no
`HOME`, as a read-only grant there does; pass `HOME` in `env=` if you need one.
A path a more specific preopen owns, spelled past the guest's C library
(`/usr/./local/lib` under a mount at `/`), is refused with `EPERM`.

**Limits** (each with a default):

- **provider calls:** `max_file_calls=` (default
  `defaults().file_calls`, 10,000). Every provider call counts, whatever it
  answers. The call that would pass the limit is not made; the run stops and
  `trapped` is `"out of file calls"`, with `exit_code` and `fuel_used` `None`;
- **open files:** at most 1,024 open files and folders per call; the next open
  answers `EMFILE` without calling the provider. They cost no host
  descriptor;
- **staged bytes:** the bytes of every open file plus every kept listing are
  at most `memory_bytes` (4 GiB with `memory_bytes=None`); a `read` that would
  pass it answers `EFBIG` and is dropped. A listing counts as the bytes the
  runner keeps for it (its encoded entries), and is judged while it is
  gathered. The bound is on what the runner keeps, not on what your provider
  made: a provider should refuse a large file before it reads it (judge
  `stat`'s size first).

**What differs from a grant.** A mount answers as a read-only grant does
(every write-type call is `EPERM`, before your provider is called), except:

- a whole file is staged at open, so a 1-byte read stages the file;
- `os.fstat` of an open file shows its kind and size but no times (`stat`
  shows `mtime_ns`); there are no links (`os.readlink` answers `EINVAL`);
- an open file's number (`f.fileno()`) is 2**30 or above, so
  `select.select` refuses it with `ValueError` (its limit is 1,024); use
  `selectors` (whose default here is a `PollSelector`, which asyncio uses)
  or `select.poll`;
- `os.lstat` (or `os.stat(..., follow_symlinks=False)`) of a file with a
  trailing `/` or `/.` is `ENOTDIR`, as `os.stat` and opening it answer
  everywhere (on Linux, a grant's `os.lstat` alone answers with the file's
  stat);
- `..` is resolved by text (`missing/../a.txt` opens `a.txt`, where a grant
  answers `ENOENT` on Linux and macOS; a Windows grant resolves it by text
  too); a climb above the folder the call starts from, even for a
  moment, is `EPERM`, as on a grant;
- a path over 4,096 bytes is `ENAMETOOLONG`, a guest pointer past its memory
  `EFAULT` (a later `iovec` past it too, where a grant reads the first
  non-empty one), more than 1,024 `iovec`s `EINVAL`: the runner's own
  answers, the same on every host; letter case is your provider's;
- a path both absolute and not UTF-8 is `EILSEQ` (the text is decoded first,
  as wasmtime decodes it);
- an argument the ABI cannot carry (an undefined flag, a misaligned pointer)
  ends the run as on a grant, with the same `fuel_used`, but `trapped` names
  it (`Invalid flag value Oflags`);
- `fd_renumber` of an open file answers `ENOTSUP`.
- each `fd_readdir` entry's three padding bytes are zeros, as on a grant: the
  runner zeroes a grant's listing too, which the wasmtime-py 49.0.0 it uses
  fills from uninitialized host memory (see *Safety*).

**Time and threads.** A provider runs synchronously on the thread that runs
the guest; under `run_async` that is a worker thread, never the event loop's.
Before each provider call the runner checks the call's `cancel` and its
deadline; if either has passed, the provider is not called. Your provider's
own time is outside the deadline and cannot be interrupted: bound its calls
yourself. A deferred Ctrl-C on the main thread waits for a blocked provider,
as it waits for a blocked door host. One provider may serve concurrent calls,
from each call's thread, so a shared provider must be thread-safe. An async
layer can be bridged from the worker thread with
`asyncio.run_coroutine_threadsafe(coro, loop).result()` until async providers
are specified; an `async def` method is refused.

`done.files` (a `FileRecord`, `None` for a call without mounts) holds `calls`,
each of the eight methods' counts (zeros included, read-only mounts too),
`faults`, the first 1,000 `FileFault(method, path, error)`, where `error` is
the exception's type and first line, or `"bad answer: <type>"`, and, for
writable mounts, `refused` and `refused_total` (below). It holds no exception
object and no times.

#### Writable mounts

`Mount(provider, guest, writable=True)` lets the guest write there: create,
write, append, truncate, make and remove folders, rename within the mount.
Nothing is writable unless you say so: `writable` is keyword-only and must be
`True` or `False` (`"yes"`, `1` or `None` is a `TypeError`), and a read-only
mount never calls the write half, whatever your provider has. A writable
mount's provider has five more methods, checked before any work (each
callable, none `async def`), each answering `None` for success or an `Errno`:

```python
class Store(Files):  # the read half above, plus:
    def write(self, path, data):  # the whole file; create it if missing
        if self.tree.get(path, b"") is None:
            return Errno.EISDIR
        self.tree[path] = data  # `data` is a bytes copy you may keep
    def mkdir(self, path):
        if path in self.tree:
            return Errno.EEXIST
        self.tree[path] = None
    def remove(self, path):  # a file; EISDIR for a folder
        ...
    def rmdir(self, path):  # an empty folder; ENOTEMPTY otherwise
        ...
    def rename(self, src, dst):  # POSIX's replace rule, within the mount
        ...

done = run(["-c", "import pandas as pd; pd.DataFrame({'a': [1]}).to_csv('/work/out.csv')"],
           mounts=[Mount(Store({}), "/work", writable=True)])
```

Each keeps POSIX's contract in preview1's numbers: `write` is `EISDIR` on a
folder, `ENOENT` for a missing parent and `ENOTDIR` for a file parent; `mkdir`
is `EEXIST` when the path exists; `remove` is `EISDIR` on a folder (Linux's
answer) and `ENOENT` when missing; `rmdir` is `ENOTEMPTY`, `ENOTDIR` or
`ENOENT`; `rename` replaces a file with a file and an empty folder with a
folder, and is `ENOTEMPTY`, `EISDIR` (a file onto a folder), `ENOTDIR` (a
folder onto a file) or `ENOENT` (no `src`). Your quotas, permissions and
conflicts (`EACCES`, `EROFS`, `ENOSPC`, `EDQUOT`, `ESTALE`, `EBUSY`,
`ETIMEDOUT`) reach the guest unchanged; the runner does not know why.

**A file exists from its open.** A create or a truncation reaches you at open
as `write(path, b"")`, so you see an empty first version of every file a guest
creates, and a create you refuse fails the `open`, as on a grant. `open(p,
"w")` is one `write(p, b"")`; `"x"` is a `stat`, then the `write` if the name
is free (exact within a call, and as atomic across writers as your `stat`
then `write`); `"a"` and `os.open(p, O_CREAT | O_WRONLY)` are a `read`, then
the `write` only if the file is missing; `"r+"` is a `read`. So
`tempfile.TemporaryFile`, `mkstemp` then `rename`, lock files and
`os.path.exists` of a file held open all behave as on a Linux or macOS grant
(a Windows grant differs, below).

**The bytes are handed over whole.** What the guest writes goes into a
buffer the runner holds for that descriptor, with no provider call. The
whole file reaches you as one `write(path, data)` when the guest closes it,
at `os.fsync` or `os.fdatasync`, and at the call's ending, whatever ends it:
an exit, `os._exit`, a trap, `"out of fuel"`, its deadline, a cancel, `"out
of file calls"`. A clean file closes with no call. So a refused write shows
at the close or the `fsync` (a `with` block or `close()` raises the
`OSError` of your `Errno`), not at the `write`. After a stop the runner makes
at most min(1,024, the file calls left) such writes, handing over at most the
staged bytes (the `memory_bytes` bound: 1 GiB by default, 4 GiB when it is
`None`): each takes your
provider's time, so a mounted run may return after its deadline by that much.
A provider that must honour the deadline answers `ETIMEDOUT`, which is
recorded. Nothing is written back when the call raises (a door host's or your
provider's `BaseException`, or a Ctrl-C), nor when the interpreter is exiting
(a `run_async` call stopped by the exit hook): provider code must not run
then, and no result could report a refusal. Bytes still in a Python buffer
when the guest stops by `os._exit` or a trap never reached the runner (a
normal exit's finalization closes Python's files).

**The record.** `done.files.refused` holds the first 1,000
`RefusedWrite(mount, method, paths, errno, at, cause)`: every write-half call
that did not succeed and every write-back the runner owed but did not make,
whatever the exit code. `paths` is the provider path, or `(src, dst)` for a
rename; `at` is `"open"`, `"call"` (a `mkdir`, `remove`, `rmdir` or
`rename`), `"close"`, `"sync"` or `"exit"`; `cause` is `"refused"` (your
`Errno`, returned or raised), `"fault"` (an exception or a bad answer, also
in `faults`, recorded as `EIO`) or `"limit"` (the file-call limit came first;
no call was made).
`refused_total` counts every one, kept or not: `len(refused) <
refused_total` says the list was cut. A refused `stat`, `list` or `read` is
the guest's answer at its open and is not recorded. Whether a refused write
fails the run is yours to decide.

**What differs from a writable grant**, each the price of whole-file staging
or a guard, none a way out of the mount:

- a file's unflushed writes are seen only through the descriptor that made
  them, until its close or `fsync` (a grant shows them at once to `stat`, a
  listing and another open);
- two descriptors on one path have two buffers, and the later write-back
  replaces the earlier;
- a write past the staged-bytes bound is `EFBIG` (a guest can grow a file to
  the bound with one `truncate`). The bound counts each buffer's length; the
  host may hold up to about an eighth more for a grown buffer (Python's
  `bytearray` over-allocates), and a write-back hands over one transient copy
  of the buffer;
- a rename or link between a mount and another writable preopen is `EXDEV`
  (`shutil.move` then copies and removes); to a read-only one, `EPERM`;
- `os.link` and `os.symlink` within a mount are `ENOTSUP`: the protocol has no
  links;
- `os.utime` and the other set-times calls succeed and change nothing, with no
  provider call: times are your provider's (`os.stat` shows your `mtime_ns`);
- a rename or `rmdir` strictly above a more specific preopen (`/usr` under a
  writable mount at `/`) is `EBUSY`, where a grant may remove a nested grant's
  empty host folder;
- the runner sees only this call's own changes: a file renamed or removed by
  you or another run while a descriptor is open is written back to the path
  the descriptor holds (a guest's own renames and removals are followed, as
  POSIX descriptors follow the file);
- a file left open when the interpreter exits during a `run_async` call is
  not written back.

**On Windows** a writable grant answers as Windows does, and a mount as it
does on every host:

- `os.rename` of a folder onto a file replaces the file on a Windows grant; a
  mount never does, and answers `ENOTDIR`, as a Linux or macOS grant does;
- a Windows grant cannot remove or rename a file the guest holds open, so
  `tempfile.TemporaryFile` and an `os.replace` inside a `NamedTemporaryFile`'s
  `with` fail there and leave their `tmp…` file; a mount allows both.

**Cost.** Every write-half call, every create at open and every write-back
counts toward `max_file_calls`. Each close or `fsync` of a changed file hands
you the whole file, so a guest that grows a file to the bound and loops
"write one byte, `fsync`" can make up to `max_file_calls` write-backs of up to
the bound each (10,000 × 1 GiB with the defaults, in practice limited by the
deadline), where a grant writes one byte per sync. A provider that persists or
versions every write should quota or rate-limit its writes and answer
`EDQUOT`.

**State across runs is yours.** A writable mount whose provider keeps its
state holds what a later run meets: modules a later run imports from it (by
adding it to its own `sys.path`; the runner never puts a mount or a writable
place there) and data
files that change a later run's answers (`/etc/mime.types`,
`/usr/share/zoneinfo/…`). Give each untrusted program its own writable
namespace, or check what it left. The runtime's own files stay the stdlib
zip's: a write, a create or a rename at or under `/usr/local/lib` (however it
is spelled) is `EPERM`, and a read-only grant inside a writable mount stays
read-only. The runner makes no `HOME` in a mount, writable or not; a writable
mount at `/tmp` holds `tempfile`'s files; pass `HOME` in `env=` if you need
one. sqlite3 over a mount is not supported (it needs ranged writes and
locking).

### From any language

`wasi-python run` runs one program and prints its result as one line of JSON, so
any language can call the runner as a subprocess:

```
$ wasi-python run -- -c "print(1)"
{"exit_code": 0, "fuel_used": null, "stderr": "", "stdout": "1\n", "trapped": null, "truncated": []}
```

```typescript
import { spawn } from "node:child_process";

const child = spawn("wasi-python", ["run", "--deadline-s", "10", "--", "-c", code]);
let out = "";
child.stdout.on("data", (chunk) => (out += chunk));
child.on("error", (err) => console.error("wasi-python could not start:", err.message));
child.on("close", (status) => {
  if (status === 0) console.log(JSON.parse(out)); // how the program ended
  else if (status === 1) console.error(JSON.parse(out).error); // run() refused or failed
  else console.error(`wasi-python exited ${status}`); // 2: usage error; 130: interrupted
});
```

Each option is one of `run`'s arguments, and nothing else: `--env KEY=VALUE`
(or `--env KEY` to pass this command's own value, which keeps a secret off the
command line), `--stdin PATH` (or `-` for this command's input), `--deadline-s`,
`--memory-bytes`, `--output-bytes` (each a number, or `none` for no limit),
`--fuel` and `--no-snapshot`. Without an option the call has `run`'s defaults.
Everything after `--` is the program's arguments.

Folders, each one of `run`'s grants (see *Grants*): `--grant GUEST=HOST` gives the
program a host folder read-only, `--grant-writable GUEST=HOST` writable; the split
is at the first `=`, so `C:\data` and host paths with `=` pass whole. `--root
HOST` is the guest's `/`, writable, and made if missing; `--private-root` gives
it a fresh private `/`, removed after the call (`root=True`); without either the
program has no `/` at all, only its grants (`--no-root` says so explicitly).
`--root` given twice, or two of the three together, is a usage error. A guest path given here cannot hold `=`. `run`'s
errors number the grants from 0, across both options, in the order typed.
`--import-path GUEST` (repeatable) puts a guest path a `--grant` serves on the
import path, in the order typed (see *The import path*). The
program itself is read from the host with `--stdin`, since the guest does not
see the host's folders, only its root and its grants:

```
$ wasi-python run --grant /data=./inputs --grant-writable /out=./results --stdin prog.py -- -
```

The line's keys: `exit_code`, `trapped`, `fuel_used` and `truncated`, as
`run` returns them, and `stdout` and `stderr` as text, or `stdout_base64` and
`stderr_base64` when the bytes are not UTF-8 (output cut at `--output-bytes`
in the middle of a character is not). The command's own exit code says whether
there is a result, not how the program ended: 0, a result; 1, `run` refused or
failed, with `{"error": …, "kind": …}`; 2, a usage error, on standard error;
130, Ctrl-C. A program's exit code 3 is `"exit_code": 3` with the command's 0.

Two cautions. The line can be up to 6 times the program's output (JSON
escaping), so collect standard output in full: Node's `exec` stops at 1 MiB by
default. A long program belongs in a file, `--stdin prog.py -- -`, not in `-c`,
which meets the system's limit on argument length.

### From async code

`run_async` takes `run`'s arguments except `cancel` (cancel its task
instead), plus `executor`, and runs the call on
a worker thread, so the event loop never waits for a guest. wasmtime
releases the GIL while wasm runs, so guests on different workers run in
parallel. An ASGI endpoint (FastAPI shown):

```python
import asyncio
from wasi_python import run_async

@app.post("/run")
async def run_code(code: str):
    async with asyncio.timeout(30):  # also bounds the time spent waiting for a worker
        done = await run_async(["-c", code])
    return {"exit_code": done.exit_code, "stdout": done.stdout.decode()}
```

- **Cancelling the task stops its guest.** The runner checks the cancel
  every 50 ms while the guest computes, and at once when it waits or calls
  the door; the check and the clean-up need the GIL, so other busy Python
  threads delay them (measured: up to 200 ms to stop and 460 ms to return
  with one other thread spinning). The worker is freed and the private
  root removed before `CancelledError` (or the timeout's `TimeoutError`)
  reaches the caller. A call still waiting for a worker never starts. A guest inside
  a door host is stopped only when the host returns: the runner cannot
  interrupt host code.
- **What cancels the task** is your code: a timeout, a task group,
  shutdown. Starlette does not cancel a plain endpoint's task when the
  client disconnects, so without a timeout that guest runs to its
  `deadline_s`.
- **How many run at once.** With no `executor`, calls share one pool per
  process of `defaults().async_workers` threads: the CPU count (with CPU
  affinity, from Python 3.13), at most 8. Further calls wait for a worker.
  At the defaults each running guest may hold 1 GiB of memory, up to
  32 MiB of output and a copy of its `stdin`, so 8 workers bound one
  process at about 8.3 GiB, plus the disk a guest writes and the file
  descriptors it opens. A new size applies to calls submitted afterwards; calls
  already running or queued on the old pool still run there, so for a while
  both pools' workers may run guests (after 8 to 4, up to 12 at once). Four server worker processes have four pools: four
  times that. A container's CPU quota is not seen; set the size with
  `set_defaults(dataclasses.replace(defaults(), async_workers=n))`. The bound covers only `run_async` on its own pool, not
  `run` called from your threads, an `executor` you pass, or a
  framework's thread pool for synchronous endpoints.
- **A synchronous endpoint** that calls `run` also keeps the loop free (the
  framework runs it on a thread), but it cannot be cancelled.
- **`executor`** must run callables on threads of this process; a process
  or interpreter pool is refused.
- **Forking.** A process forked after it ran a guest refuses to run guests
  (`RuntimeError`): wasmtime does not support use across a fork. Warm the
  runner up after the fork (in gunicorn's `post_fork`, say), never before.
- **Exit.** At interpreter exit, `run_async`'s running guests are stopped
  together and its queued calls dropped, so exit waits about as long as
  one cancel, longer for a worker inside a door host or still compiling.
  On a Python without `threading._register_atexit` (CPython has had it
  since 3.9) the stop runs later, and exit can wait for queued calls.
- **A host function that must await** is best served as an async tool
  (see *Tools*, **Async tools**): the runner awaits it on your loop, bounds
  it by the call's deadline and cancel, and cancels it when its call ends.
  A raw `host=` must stay synchronous (an `async def` is refused); one
  that must await runs the coroutine on its own loop with
  `asyncio.run_coroutine_threadsafe(coro, loop).result(timeout=...)`;
  without a timeout a closing loop blocks it forever.
- `run_async` is asyncio only. Under trio, call `run(cancel=event)` from a
  worker thread.

Any other embedder does the same three things:

1. **Preopen the artifact set's stdlib zip, read-only, in a folder of its
   own at `/usr/local/lib`** (the guest finds `/usr/local/lib/python315.zip`),
   plus whatever folders the embedder grants, possibly none, a folder at `/`
   included. The snapshot runs only beside the zip it was built against.
2. **Bind the one custom import, `host::call(ptr, len, out_ptr_ptr,
   out_len_ptr) -> i32`.** Answer −1 when there is no host. Otherwise read
   the request from guest memory, get space from the exported `host_alloc`,
   write the response, store its pointer and length at the two
   out-addresses, and answer 0; answer −2 if the host fails. Frames are
   opaque bytes: their meaning is the embedder's.
3. **Call `_initialize`** (the plain reactor only) **and then `run`**,
   once per instance, with argv (`argv[0]` is `/usr/local/bin/python.wasm`)
   and the environment given through WASI. `run` returns the exit status.

The import path holds only the stdlib zip. A host that adds entries should add
read-only ones only, after the zip; since it owns argv, it may do it as the
runner does, with a `-c` prelude that extends `sys.path` and then calls
`_reactor.run(argv, environ)`.

The plain `wasmtime run` CLI cannot bind a custom import and refuses the
binary. With `-W unknown-imports-default` it runs it, but the door then
answers 0 with no response, which guest code reads as an empty answer.

### Tools

`run(tools=[…])` offers the guest your Python functions. Guest code imports
them with `from host import tools` and calls them like functions. Between
the two run JSON frames, protocol 1 (see *The tool protocol*):

```python
from wasi_python import run
from wasi_python.tools import ToolError, tool

REGIONS = {"EMEA": {"code": "EMEA", "manager": "Ada"}}

@tool(read_only=True)
def lookup_region(code: str) -> dict:
    """Look up a sales region by its code.

    Args:
        code: The region code, such as "EMEA".
    """
    if code not in REGIONS:
        raise ToolError(f"no region {code!r}")  # the guest reads this message
    return REGIONS[code]

program = """
from host import tools
print(tools.lookup_region("EMEA")["manager"])
"""
done = run(["-c", program], tools=[lookup_region])
done.stdout                                    # b'Ada\n'
[o.outcome for o in done.tools.outcomes]       # ['ok', 'ok']: the list, then the call
```

- **The decorator.** `tool()` takes the name, the description and the input
  schema from the function: its type hints, its docstring up to the first
  heading, and its `Args:` section. `input_schema=` gives the schema instead,
  as a dict or a pydantic model. A plain function in `tools=` goes through
  `tool()`. The guest's function has the same signature and docstring
  (`help(tools)`), and `wasi_python.tools.stubs(tools)` renders them for a
  prompt.
- **A tool runs with your process's authority.** A `read_file(path)` tool is
  a filesystem, and a `sql(query)` tool is your database: the guest may call
  it with any arguments its schema allows. So pass capabilities, not
  services. Make the tools per request, each closing over that caller's
  authority:

  ```python
  def tools_for(user):
      @tool
      def my_orders(limit: int = 10) -> list[dict]:
          """This user's latest orders."""
          return orders.latest(user_id=user.id, limit=min(limit, 50))

      return [my_orders]

  done = run(["-c", code], tools=tools_for(request.user))
  ```

  A `functools.partial` binds authority too:
  `tool(partial(orders_for, user_id=user.id, api_key=KEY), name="my_orders")`.
  A keyword the partial binds is fixed. It is not in the schema, so the
  guest never sees its value, and a frame that names it is refused as an
  unknown argument, so the guest cannot replace it. A positional argument
  it binds is fixed the same way. A bound value need not be JSON: bind a
  database connection if you like. A `functools.partialmethod` works
  through an instance (`obj.method`). A parameter's own default is not
  fixed: it is published in the schema (the guest's signature and
  `stubs()` show it) and the guest may pass another value. So never put
  authority, such as a key or a user id, in a default.

- **The gate.** `gate=` is called before each tool runs, with a
  `ToolCall`: `seq`, `tool`, a copy of the validated `arguments`, and
  `request_bytes`. `arguments` holds only what the guest sent: no default,
  and no keyword a partial binds. A gate that judges the values the tool
  will use fills in the defaults itself. It allows by returning `None` or `True`. It refuses by
  raising `ToolDenied(message)`, whose message the guest reads as a
  `PermissionError`, or by returning `False`. A gate that raises anything
  else refuses too, and the record keeps its fault. With no gate, every
  valid call runs: your choice of tools is then the policy.
- **The record.** `done.tools` is a `ToolRecord`: `frames` (every frame
  counted), `outcomes` (the first 1,000: `seq`, `op`, `tool`, `outcome`,
  `message`, `request_bytes`, `response_bytes`, `fault`, `abandoned`),
  `unlisted`, and `abandoned`: every call answered while its tool ran on,
  listed or not, so 1,000 cheap frames cannot hide one. It comes back on every ending: an exit, a trap, `"deadline"`
  and `"cancelled"`. It is `None` for a call without `tools=`. Nothing in it
  measures time.
- **Errors stay on the host.** Nothing the guest, a gate or a tool does makes
  `run` raise. A tool's `ToolError` message crosses (`tool_error`), and so
  does a `ToolDenied` (`denied`). Any other exception crosses only as "<name>
  failed (internal error)"; the record's `fault` keeps its type and first
  line, so a path in an exception never reaches the guest. A result must be
  JSON: numpy's integers and floats are, but numpy's `bool_` is not, so
  return `bool(df["x"].any())`, not `df["x"].any()`.
- **Limits.** At most `max_tool_calls` frames per call, the guest's discovery
  frame included (default `defaults().tool_calls`, 1,000; `None` means no
  limit). At most `max_tool_request_bytes` bytes of requests read per call
  (default `defaults().tool_request_bytes`, 16 MiB; `None` means no limit),
  counted from each frame's length before it is read, whatever its answer: a
  frame that would pass it is refused unread. Past either, the guest gets
  `ToolBudgetExceeded` and runs on; the message says which. A request
  over 1 MiB is refused from its length, before its bytes are copied out of
  guest memory, so a refused frame costs the host the same whatever its
  size; an answer over 16 MiB is `too_large`. Arguments are checked within a
  budget of 100,000 steps (see *The tool protocol*). Bulk data belongs on a
  writable mount (see *Mounts*), whose provider gets it without a JSON
  parse, not in tool arguments.
- **The host's cost per frame.** Two limits bound it, each its own part.
  Parsing and checking a frame the door admits costs in proportion to its
  bytes, in Python on the door's thread, holding the GIL: a few tenths of a
  second of CPU per 1 MiB frame (0.27 to 0.65 s on an arm64 Mac, measured by
  the 0.1.0a4 security review), even one that names no tool, while sending it
  again costs the guest almost no fuel. `max_tool_request_bytes` bounds that:
  at the default 16 MiB, about 5 to 10 s of host CPU for the worst frames.
  Every frame also has a small fixed cost (about 20 µs read, 3 µs refused),
  and a `list` frame copies the tool list, encoded once per call, into guest
  memory; `max_tool_calls` bounds those, since it bounds the frames. With a
  limit set to `None`, only the deadline bounds what it bounded. Where many
  untrusted guests run at once, lower both, and the deadline.
- **Tools run on their own threads.** Each tool call runs its gate, its tool
  and its result's encoding on a new daemon thread, in a copy of the
  caller's `contextvars` context. The call's deadline, its `cancel` and
  Ctrl-C must be answered while a tool blocks, and host code cannot be
  interrupted; only a thread waiting beside the tool can answer in time. So
  objects bound to a thread do not work inside a tool or a gate: a `sqlite3`
  connection made with `check_same_thread` (the default), or a
  `threading.local`. Context variables do.
- **Time.** A tool call ends at the first of: the tool's `timeout_s`
  (`tool(timeout_s=…)`); two ticks (20 ms) before the run's deadline; the
  run's `cancel`, or the `run_async` task's cancellation; and Ctrl-C. A
  timeout raises `ToolTimeout` (also a `TimeoutError`) in the guest, which
  runs on. A cancel or Ctrl-C answers `cancelled`, and the run then stops as
  `"cancelled"` or raises `KeyboardInterrupt`. There is no per-call default
  beyond the run's deadline. Fuel counts only the guest's instructions: time
  spent in a tool adds none.
- **Abandoned tools.** A sync function cannot be stopped (an async one can:
  see **Async tools**). A tool whose
  call timed out or was cancelled runs on to its end, unseen; its result is
  dropped, and its outcome says `abandoned=True`, because its effect may
  still land. So a call the guest retries after `ToolTimeout` may act twice.
  A call that timed out or was cancelled while its gate was still deciding
  never starts its tool, even if the gate then allows: only the gate ran
  on, and the outcome says `abandoned=True` too.
  One run may hold 4 abandoned tool threads; while it does, its next tool
  call is answered `timeout` at once, without running. The bound is per run,
  not per process: each run can leave up to five threads behind (four
  abandoned, and the one running when the run ended), and there is no
  process-wide ceiling, which would let one run's stalled tools starve
  another's. A tool that can hang must bound itself (a timeout on its own
  network call). `wasi_python.stats()["tool_threads_running"]`
  counts the tool threads alive in the process, abandoned ones included.
- **What `run` refuses**, before any work: `host=` with `tools=` (the door
  is one function: pass `host=` for the raw door or `tools=` for the
  protocol), `gate=`, `max_tool_calls=` or `max_tool_request_bytes=` without
  `tools=`, two tools with
  one name, an async generator function as a tool or a gate (a tool answers
  each call once), an `async def` as `host=` (the raw door is synchronous:
  serve it as a tool), and an artifact set from before the tool protocol
  (`ArtifactsMissing`).
- **Async tools.** A tool or a gate may be an `async def`, or a function
  that returns an awaitable (an adapter over an async client). The guest
  still calls it synchronously; only the host side awaits.

  ```python
  import asyncio
  from wasi_python import run_async
  from wasi_python.tools import tool

  PRICES = {"EUR": 1.08, "GBP": 1.27}

  @tool
  async def rate(currency: str) -> float:
      """The US dollar price of one unit of a currency."""
      await asyncio.sleep(0)  # your async client's call goes here
      return PRICES[currency]

  async def main():
      code = "from host import tools\nprint(tools.rate('EUR'))"
      done = await run_async(["-c", code], tools=[rate])
      return done.stdout                     # b'1.08\n'

  asyncio.run(main())
  ```

  - **Where it runs.** Under `run_async`, on the event loop that awaits
    `run_async`, beside your own sessions and clients, so objects bound to
    that loop work. Under `run`, on a loop of the call's own, on a thread
    named `wasi-python-tool--loop` that is started at the call's first
    awaitable and closed when the call ends; each call gets its own, so one
    call's tool that blocks its loop delays no other call's. Use
    `run_async` when your tool needs your loop's objects: `run` on a worker
    thread (`asyncio.to_thread(run, …)`) gets a loop of its own.
  - **Stopped, not abandoned.** A call answered before its coroutine has
    started (its timeout or the deadline came first, or its gate answered
    late) never starts it. Once started, every end of the call (`timeout_s`,
    the deadline, a cancel, Ctrl-C) cancels it at its next `await`. A
    coroutine that catches `CancelledError` and goes on runs on, holds one
    of the run's 4 abandoned slots, and keeps its thread alive, like a sync
    tool.
  - **Faults stay in the call.** A `KeyboardInterrupt`, `SystemExit` or
    `CancelledError` the tool raises, or a loop that has closed or stopped,
    is a "(internal error)" fault in the record, never an exception in
    your loop. A `CancelledError` met while the run is being cancelled is
    answered `cancelled`.
    Tasks the tool spawns are yours: under `run_async` their exceptions
    reach your loop as asyncio delivers them, so a `KeyboardInterrupt` from
    one reaches your `asyncio.run`.
  - **What it does not do.** Under `run_async`, tasks an async tool spawns
    outlive the call: the runner cancels only its own (under `run`, the
    call's loop cancels everything on it when it closes). An abandoned
    coroutine that ignores its cancel on your loop keeps that loop's
    `asyncio.run()` from returning at shutdown, since `asyncio.run` waits
    for every task; an abandoned sync tool never does, its thread being a
    daemon. A blocking call inside an `async def` holds the loop it runs
    on, and every async tool on that loop with it.
  - **Counted.** `tool_threads_running` counts the call's loop thread with
    the tool threads while it is alive; threads a tool starts itself
    (`asyncio.to_thread` on that loop's default executor) are not counted.

Two recipes follow. They are recipes, not API: the project ships no
adapter, and each was run once with the versions named (specs 036's and
053's landing notes).

**A LangChain tool** (`langchain-core==1.6.12`), its own input checked by
its own pydantic model:

```python
from langchain_core.tools import ToolException
from wasi_python.tools import ToolError, tool

def from_langchain(lc_tool):
    def call(**args):
        try:
            return lc_tool.invoke(args)
        except ToolException as e:
            raise ToolError(str(e)) from None  # its text is meant for the caller

    return tool(call, name=lc_tool.name, description=lc_tool.description,
                input_schema=lc_tool.args_schema, validates_input=True)
```

**An MCP server's tool**, through your own client session (`mcp==2.3.0`).
The session lives on your event loop, and an async tool is awaited there:
`run_async` keeps the loop free meanwhile, and a call that times out or is
cancelled cancels its `call_tool`. The result's structured content
(`structuredContent` on the wire, `structured_content` in mcp 2's Python)
is the value, and an error result (`isError`) becomes a `ToolError` with the
server's text:

```python
from wasi_python import run_async
from wasi_python.tools import ToolError, tool

def from_mcp(session, listed, timeout_s=30):
    async def call(**args):
        result = await session.call_tool(listed.name, args)
        text = " ".join(c.text for c in result.content if c.type == "text")
        if result.is_error:
            raise ToolError(text)
        return result.structured_content if result.structured_content is not None else text

    return tool(call, name=listed.name, description=listed.description or "",
                input_schema=listed.input_schema, validates_input=True, timeout_s=timeout_s)

async def answer(session, code):  # session: your open mcp.Client
    tools = [from_mcp(session, t) for t in (await session.list_tools()).tools]
    return await run_async(["-c", code], tools=tools)
```

An MCP tool whose name or property names are not Python identifiers needs
`name=` and a renamed schema, as *The tool protocol* shows under **Names**.

### The tool protocol

On top of the door the project ships one protocol, through which guest code
calls the host's tools: `from host import tools`, then
`tools.lookup_region("EMEA")`. The guest's half is the pure-Python package
`host` in the stdlib zip. The host's half in Python is `wasi_python.tools`
(`tool()`, `stubs()`), which `run(tools=…)` binds to the door (see *Tools*).
An embedder in another language serves the protocol from its own
door function, by the rules below. It is optional: a door that never answers
it leaves `from host import tools` raising `ImportError`.

**Frames.** One compact UTF-8 JSON object per door call, each way. `v` is
the protocol version, 1; `id` is the guest's number for the frame, echoed when
it is an integer from 0 to 2**53 - 1, else `null`, and never trusted.

```text
request    {"v": 1, "id": 7, "op": "list"}
           {"v": 1, "id": 8, "op": "call", "tool": "lookup_region", "args": {"code": "EMEA"}}
answer     {"v": 1, "id": 7, "ok": true, "tools": [descriptor, ...]}
           {"v": 1, "id": 8, "ok": true, "value": <JSON>}
           {"v": 1, "id": 8, "ok": false, "error": {"kind": "denied", "message": "..."}}
descriptor {"name", "description", "inputSchema", "outputSchema"?, "annotations"?}
bytes      {"$bytes": "<base64>"}
```

The descriptor uses MCP's field names. The `list` answer keeps the order the
embedder gave the tools. An unknown version or operation is a `protocol`
answer naming what the host serves; `batch` is reserved. A field a peer may
ignore can be added within a version; one it must act on bumps `v`.

**Kinds**, and what the guest raises (each a `host.ToolError`, with the kind
in `.kind`):

| kind | guest class | when |
|---|---|---|
| `protocol` | `ToolProtocolError` | the frame breaks a rule below, or the answer does not match |
| `unknown_tool` | `ToolArgumentError` (also `TypeError`) | no tool has that name |
| `invalid_arguments` | `ToolArgumentError` | the arguments do not fit the input schema |
| `denied` | `ToolDenied` (also `PermissionError`) | the gate or the tool refused |
| `tool_error` | `ToolError` | the tool failed; only a message it chose crosses |
| `timeout` | `ToolTimeout` (also `TimeoutError`) | the call ran out of time |
| `cancelled` | `ToolCancelled` | the run was cancelled during the call |
| `too_large` | `ToolTooLarge` | a request over 1 MiB, or an answer over 16 MiB |
| `budget_exceeded` | `ToolBudgetExceeded` | the run's frames are used up (1,000 by default), or its request bytes (16 MiB by default) |

A cancelled run is stopped at the guest's next function entry, so do not rely
on `except ToolCancelled` for clean-up.

**The rules for a request**, in this order, before any schema is read; each
failure is a `protocol` answer. They are the protocol's own, so the answer is
the same whatever the host's Python or its settings:

1. at most 1 MiB, judged from the length before the bytes are read;
2. strict UTF-8 (never UTF-16 or UTF-32);
3. nested at most 64 levels, its envelope included, counted outside strings
   (so 62 levels inside `args`);
4. JSON with no `NaN` or `Infinity`, no number that overflows a double
   (`1e400`), no integer literal over 64 characters, and no repeated key;
5. no lone surrogate (`"\ud800"`) in a key or a value; a surrogate pair is
   fine;
6. an object at the top.

Then a `{"$bytes": "<base64>"}` object, exactly that one key holding strict
base64, becomes bytes; any other `$bytes` object is a `protocol` answer. Then
the version, the operation, the tool's name (`unknown_tool`), and the
arguments against the tool's input schema (`invalid_arguments`). Every frame
counts toward the run's budget, the guest's discovery frame included; past it
the guest gets `ToolBudgetExceeded` and runs on. Answers are encoded as ASCII
JSON, so an echoed lone surrogate still encodes. A message is at most 4,096
characters, and each piece of guest text it repeats is cut to 64 first.

**The schema subset.** The validator checks `type`, `enum`, `const`,
`properties`, `required`, `additionalProperties` (a boolean or a schema;
absent, it closes an object schema that lists `properties`, which is
stricter than JSON Schema), `minProperties`, `maxProperties`, `items` (one
schema), `prefixItems`, `minItems`, `maxItems`, `uniqueItems`, `anyOf`,
`oneOf`, a local `$ref` into `$defs` or `definitions`, the four numeric bounds,
`multipleOf` (a positive integer), `minLength` and `maxLength` (in code points),
and `contentEncoding: "base64"`. It ignores the annotations (`title`,
`description`, `default`, `examples`, `format`, `deprecated`, `readOnly`,
`writeOnly`, `contentMediaType`, `discriminator`, `$schema`, `$id`,
`$comment`). `tool()` refuses any other keyword unless the tool checks its
own input (`validates_input=True`, and then those keywords are skipped).
`pattern` is among them on purpose: an embedder's regular expression run on a
megabyte of guest text can backtrack without end. The array form of `items`,
a `$ref` that is not local, and a `$ref` cycle that never descends into the
value are refused even then.

- **No coercion.** `integer` is an integer, never `true` and never `5.0`
  (stricter than JSON Schema); `number` is never a boolean. `enum`, `const`
  and `uniqueItems` compare by JSON type and value: `true` never equals `1`,
  and `1.0` never equals `1`.
- **Bytes** are accepted only where the schema says `{"type": "string",
  "contentEncoding": "base64"}`, never where it says nothing.
- **A budget of 100,000 steps per frame,** past which the call is
  `invalid_arguments`, "the arguments are too complex to check". A value
  costs one step for each schema node it is checked against: its own, each
  `$ref`, `anyOf` or `oneOf` around it, and each `anyOf` branch tried; a
  node that only delegates never walks the value again. A key for `enum`,
  `const` or `uniqueItems` costs one step per value below it (and a
  `uniqueItems` key one more); an `enum` is a set made once, so checking a
  value against it is one lookup. So ordinary arguments cost one to two and
  a half steps per JSON value, whatever their depth (pydantic's shapes:
  about 1.4 for a list of models, about 2.3 for a recursive tree with an
  optional parent). Validation runs on the door's thread, where no deadline
  or cancel can stop host code, and a recursive schema whose `anyOf`
  branches overlap would otherwise double its work at each level. A call
  with more than about 50,000 values is bulk data, which belongs in a
  granted folder. A chain of `$ref`, `anyOf` and `oneOf` on one value is at
  most 8 schema nodes.

**Results** cross as JSON: a dict with `str` keys, a list or tuple, `str`,
`bool`, `int`, a finite `float`, `None`, bytes as `$bytes`, and numpy's
scalars as `int` or `float`. Anything else, an exception that is not a
`ToolError`, or a gate that raises anything but `ToolDenied` or `ToolError`,
reaches the guest only as "<name> failed (internal error)" or "<name> was
refused"; the host's record keeps the exception's type and first line.

**Names.** A tool's name is a letter, then up to 63 letters, digits or
underscores, and not a Python keyword. The guest calls a tool with its
properties as keyword arguments, so `tool()` refuses a property that is not
a Python identifier or is a keyword (`from`, `class`, `max-results`). Rename
it, and map it back in the function:

```python
from wasi_python.tools import tool

schema = {"type": "object", "properties": {"sender": {"type": "string"}},
          "required": ["sender"]}

@tool(name="search_mail", input_schema=schema)
def search_mail(**args):
    return mail.search(**{"from": args["sender"]})
```

`stubs(tools)` renders each tool as the `def` line and docstring the guest's
function carries, under `from host import tools`, for a prompt.

## API reference

The public API is the names below: what `wasi_python` and
`wasi_python.tools` export (each module's `__all__`), the `wasi-python`
command, and the environment variables `WASI_PYTHON_ARTIFACTS` and
`WASI_PYTHON_CACHE`. Everything else is internal and may change in any
release: every other name, and the modules `runner`, `mounts` and `cli`.
`tests/public_api.txt` records this surface. The judge fails on any change
to it until the snapshot is regenerated, and a regeneration is made only by
a specification that lists the change, which its review checks.

The promise starts at 0.1.0, the first final release; alphas may still
change anything. Versions are `0.MINOR.PATCH`. A patch release changes no
public name, signature, field, default or command option. A minor release
may add names, keyword-only arguments whose default keeps today's
behaviour, dataclass fields placed last with a default (or keyword-only),
`Errno` members, `stats()` keys, command options and JSON keys. It
removes or changes something only after a deprecation: a
`DeprecationWarning`, a docstring that begins "Deprecated since 0.N: use X
instead." and a CHANGELOG line, all at once. A thing deprecated in 0.N still
works in 0.N and 0.N+1; 0.N+2 is the first release that may remove it. Two
exceptions need no deprecation: a tighter default limit, in a minor release,
and a security fix, in any release; each is named in the CHANGELOG.
Exceptions are promised by type, never by message. Not promised: messages,
`repr`s, help text, wasmtime's trap names and error types, timings, fuel
counts, the `.cwasm` cache, and the guest's package versions. The tool
protocol is versioned by `PROTOCOL`. At 1.0 the same rules hold with
"major" in place of "minor".

<!-- api reference: begin (generated by tests/harness/api.py) -->

### `wasi_python`

#### `wasi_python.Artifacts`

```python
@dataclass(frozen=True)
class Artifacts:
    snapshot: Path
    plain: Path
    stdlib_zip: Path
    manifest: Path
```

The artifact set's four files, made by `artifacts()`, or by you for `run(artifacts=…)`.

**Attributes:**

- `snapshot`: The snapshot binary, python-snapshot.wasm: the reactor with the stack pre-imported.
- `plain`: The plain reactor, python.wasm, without the snapshot.
- `stdlib_zip`: The stdlib zip, python-stdlib.zip, which every guest sees read-only at /usr/local/lib.
- `manifest`: The MANIFEST: every pinned source and recipe hash the build used.

#### `wasi_python.ArtifactsMissing`

```python
class ArtifactsMissing(RuntimeError):
    ...
```

Raised when there is no usable artifact set; the message says how to get one.

#### `wasi_python.Completed`

```python
@dataclass(frozen=True)
class Completed:
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    trapped: str | None
    fuel_used: int | None
    truncated: tuple[str, ...] = ()
    files: FileRecord | None = None
    tools: ToolRecord | None = None
```

How one program ended: what `run` returns.

**Attributes:**

- `exit_code`: The program's exit status: its return value, or the code it passed to exit. `None` when it trapped.
- `stdout`: What the guest wrote to standard output, up to the output limit.
- `stderr`: What the guest wrote to standard error, up to the output limit.
- `trapped`: `None` when the program ended by itself. Otherwise one of four fixed strings, "out of fuel", "deadline", "cancelled" or "out of file calls", or wasmtime's words: a trap's plain name ("stack overflow"), or an error's first line. The four strings are promised; wasmtime's words are not.
- `fuel_used`: The guest's instructions spent, when a `fuel` cap was given and no deadline hit; else `None`.
- `truncated`: The streams ("stdout", "stderr") whose output passed the limit.
- `files`: For a call with mounts, its provider calls, faults and refused writes; else `None`.
- `tools`: For a call with tools, every frame counted and the first 1,000 listed; else `None`.

#### `wasi_python.Defaults`

```python
@dataclass(frozen=True)
class Defaults:
    memory_bytes: int | None
    deadline_s: float | None
    output_bytes: int | None
    async_workers: int = <factory>
    file_calls: int | None = 10000
    tool_calls: int | None = 1000
    tool_request_bytes: int | None = 16777216
```

The limits a call has when it names none: `defaults()` returns the ones in force, and `set_defaults()` replaces them.

**Attributes:**

- `memory_bytes`: The most linear memory a guest may hold, in bytes.
- `deadline_s`: The wall-clock seconds a call may run, enforced by epoch interruption, which costs nothing per instruction.
- `output_bytes`: The most bytes kept per stream; bytes past it are dropped and the stream is named in `truncated`.
- `async_workers`: How many guests `run_async`'s own pool runs at once; by default the CPU count, at most 8.
- `file_calls`: The most provider calls a call with mounts makes; then it ends "out of file calls".
- `tool_calls`: The most tool-protocol frames a call with tools answers; past it the guest gets `ToolBudgetExceeded`.
- `tool_request_bytes`: The most bytes of tool-protocol requests a call with tools reads, counted from each frame's length before it is read; a frame that would pass it is refused unread, and the guest gets `ToolBudgetExceeded`.

#### `wasi_python.Errno`

```python
class Errno(IntEnum):
    EACCES = 2
    EBUSY = 10
    ECANCELED = 11
    EDQUOT = 19
    EEXIST = 20
    EFBIG = 22
    EINVAL = 28
    EIO = 29
    EISDIR = 31
    ENAMETOOLONG = 37
    ENOENT = 44
    ENOSPC = 51
    ENOSYS = 52
    ENOTDIR = 54
    ENOTEMPTY = 55
    ENOTSUP = 58
    EPERM = 63
    EROFS = 69
    ESTALE = 72
    ETIMEDOUT = 73
    EXDEV = 75
```

An answer a provider gives instead of a value: WASI preview1's numbers, which the guest sees unchanged, each as the `OSError` of that errno. The set is closed: no success, nothing that makes the guest's C library retry, and nothing that describes the guest's own arguments.

#### `wasi_python.FileFault`

```python
@dataclass(frozen=True)
class FileFault:
    method: str
    path: str
    error: str
```

One provider call that raised an exception that is not an answer, or answered outside its protocol.

**Attributes:**

- `method`: The provider's method, such as "read".
- `path`: The path it was given; a rename's source.
- `error`: The exception's type and first line, or "bad answer: <type>".

#### `wasi_python.FileProvider`

```python
class FileProvider:
    def stat(self, path: str) -> Stat | Errno
    def list(self, path: str) -> Iterable[tuple[str, str]] | Errno
    def read(self, path: str) -> bytes | bytearray | memoryview | Errno
```

What a mount's provider answers, for type checkers: a read-only mount's three methods.

**Methods:**

- `FileProvider.stat`: What the path is: a `Stat`, whose kind for / must be "dir", or an `Errno`.
  - `path`: An absolute path within the mount.
- `FileProvider.list`: A folder's entries, as (name, kind) pairs, or an `Errno`.
  - `path`: An absolute path within the mount.
- `FileProvider.read`: A file's whole content, or an `Errno`: EISDIR when the path itself is a folder, and ENOTDIR when a parent is a file.
  - `path`: An absolute path within the mount.

#### `wasi_python.FileRecord`

```python
@dataclass(frozen=True)
class FileRecord:
    calls: Mapping[str, int]
    faults: tuple[FileFault, ...] = ()
    refused: tuple[RefusedWrite, ...] = ()
    refused_total: int = 0
```

A call's provider calls, counted. No times, and no exception objects, so a result holds no frame of the call.

**Attributes:**

- `calls`: Each method's count, all eight methods, zeros included.
- `faults`: The first 1,000 faults.
- `refused`: The first 1,000 refused writes.
- `refused_total`: How many writes were refused in all, so a cut list says so.

#### `wasi_python.Grant`

```python
@dataclass(frozen=True)
class Grant:
    host: str | os.PathLike[str]
    guest: str
    writable: bool = False  # keyword-only
```

A host folder the guest sees at a guest path, read-only unless `writable=True`.

**Attributes:**

- `host`: The host folder, a str or os.PathLike[str].
- `guest`: Where the guest sees it: an absolute guest path, not / and not the runtime's own /usr/local/lib.
- `writable`: Whether the guest may write there. Keyword-only.

#### `wasi_python.Mount`

```python
@dataclass(frozen=True)
class Mount:
    provider: FileProvider
    guest: str
    writable: bool = False  # keyword-only
```

A provider whose files the guest sees at a guest path, read-only unless `writable=True`.

**Attributes:**

- `provider`: The provider: a `FileProvider`, or a `WritableFileProvider` for a writable mount.
- `guest`: Where the guest sees it: an absolute guest path, or / for the guest's whole filesystem (not with `root=`).
- `writable`: Whether the guest may write there; it needs the provider's write half. Keyword-only.

#### `wasi_python.RefusedWrite`

```python
@dataclass(frozen=True)
class RefusedWrite:
    mount: str
    method: str
    paths: tuple[str, ...]
    errno: Errno
    at: str
    cause: str
```

One write-half call the provider did not accept, or a write-back the runner owed and did not make.

**Attributes:**

- `mount`: The mount's guest path.
- `method`: The provider's method, such as "write".
- `paths`: The provider path, or (src, dst) for a rename.
- `errno`: The provider's answer, or EIO for a fault or the limit.
- `at`: When: "open", "call", "close", "sync" or "exit".
- `cause`: Why: "refused", "fault" or "limit".

#### `wasi_python.Stat`

```python
@dataclass(frozen=True)
class Stat:
    kind: str
    size: int = 0
    mtime_ns: int = 0
```

What a provider's `stat` answers for a path.

**Attributes:**

- `kind`: "file" or "dir".
- `size`: The size in bytes, 0 to 2**63 - 1. A bool is refused.
- `mtime_ns`: The modification time in nanoseconds, 0 to 2**64 - 1. A bool is refused.

#### `wasi_python.WritableFileProvider`

```python
class WritableFileProvider(FileProvider):
    def write(
        self,
        path: str,
        data: bytes,
    ) -> None | Errno
    def mkdir(self, path: str) -> None | Errno
    def remove(self, path: str) -> None | Errno
    def rmdir(self, path: str) -> None | Errno
    def rename(
        self,
        src: str,
        dst: str,
    ) -> None | Errno
```

What a writable mount's provider answers, for type checkers: the read half and the write half.

**Methods:**

- `WritableFileProvider.write`: Replace a file's whole content, creating the file if it is missing.
  - `path`: An absolute path within the mount.
  - `data`: The file's new content, a copy the provider may keep.
- `WritableFileProvider.mkdir`: Make a folder.
  - `path`: An absolute path within the mount.
- `WritableFileProvider.remove`: Remove a file; EISDIR for a folder.
  - `path`: An absolute path within the mount.
- `WritableFileProvider.rmdir`: Remove a folder; ENOTEMPTY for one that holds anything.
  - `path`: An absolute path within the mount.
- `WritableFileProvider.rename`: Move a file or folder within the mount, by POSIX's rule for replacing `dst`.
  - `src`: The absolute path, within the mount, of what moves.
  - `dst`: The absolute path, within the mount, it moves to.

#### `wasi_python.artifact_dir`

```python
def artifact_dir() -> Path
```

The folder holding the artifact set.

**Raises:**

- `ArtifactsMissing`: None of the three is there.

#### `wasi_python.artifacts`

```python
def artifacts() -> Artifacts
```

The artifact set's paths, in the folder `artifact_dir()` names.

**Raises:**

- `ArtifactsMissing`: There is no artifact set, or its folder has no MANIFEST; the message says how to get one.

#### `wasi_python.defaults`

```python
def defaults() -> Defaults
```

The `Defaults` a call reads now: the limits it has for each one it does not name.

#### `wasi_python.run`

```python
def run(
    argv: Iterable[str],
    *,
    root: str | os.PathLike[str] | bool | None = False,
    grants: Iterable[Grant] = (),
    mounts: Iterable[Mount] = (),
    import_path: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    stdin: bytes | bytearray | memoryview | None = None,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = <default>,
    memory_bytes: int | None = <default>,
    output_bytes: int | None = <default>,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    cancel: threading.Event | None = None,
    max_file_calls: int | None = <default>,
    tools: Iterable[Tool | Callable[..., Any]] | None = None,
    gate: Callable[[ToolCall], Any] | None = None,
    max_tool_calls: int | None = <default>,
    max_tool_request_bytes: int | None = <default>,
) -> Completed
```

Run one program in a fresh instance of the runtime and return how it ended.

**Args:**

- `argv`: The guest's arguments after the program's name, as for `python`: `["-c", code]`, `["script.py"]` or `["-m", "module"]`.
- `root`: The host folder the guest sees as /, writable, made if missing. `False` or `None` (the default) gives no / and nothing writable; `True` gives a fresh private folder, removed after the call.
- `grants`: Host folders the guest sees at their guest paths, each a `Grant`, read-only unless it says `writable=True`. The stdlib zip is always granted, read-only, at /usr/local/lib.
- `mounts`: Providers whose files the guest sees at their guest paths, each a `Mount`, served from your code, read-only unless it says `writable=True`.
- `import_path`: Guest paths put on the guest's `sys.path` after the stdlib zip, in order: each a folder or a zip file inside a read-only grant. The root, a writable grant or a mount may not serve one, no writable grant or mount may lie under one, and no writable grant or root may lie inside the grant serving one.
- `env`: Environment variables laid over the guest's own: TMPDIR=/tmp, PYTHONTZPATH= empty (zoneinfo reads the zip's tzdata), and a HOME made fresh for the call where /tmp is writable.
- `stdin`: The guest's standard input, whole; `None` is empty.
- `host`: The door's host function: called with each request's bytes, it returns the response's. It must answer synchronously: an async one raises `TypeError`. Excludes `tools`.
- `snapshot`: `True` runs the snapshot binary, with the stack pre-imported; `False` the plain reactor.
- `fuel`: A cap on the guest's executed instructions; past it the call ends "out of fuel". `None` (the default) sets no cap.
- `deadline_s`: Wall-clock seconds; past them the call ends "deadline". Default: `defaults().deadline_s`, 60. `None` means no limit.
- `memory_bytes`: The most linear memory the guest may hold, in bytes. Default: `defaults().memory_bytes`, 1 GiB. `None` means no limit.
- `output_bytes`: The most bytes kept per stream; the rest are dropped and the stream named in `truncated`. Default: `defaults().output_bytes`, 16 MiB. `None` means no limit.
- `cache_dir`: Where compiled modules are kept as .cwasm files, a folder only you can write. `None` or `True` uses `$WASI_PYTHON_CACHE`, else the user's cache folder; `False` keeps them in this process only, never on disk.
- `artifacts`: The artifact set to run; `None` finds it with `artifacts()`.
- `cancel`: A `threading.Event`. Once it is set and the guest runs, the guest stops within 5 ticks of 10 ms while it computes, and the call ends "cancelled".
- `max_file_calls`: The most provider calls a call with mounts makes; then it ends "out of file calls". Default: `defaults().file_calls`, 10,000. `None` means no limit.
- `tools`: Host functions offered to the guest through the tool protocol (`from host import tools`), each a `wasi_python.tools.Tool` or a plain function, which goes through `tool()`. A tool may be async (an `async def`, or a function returning an awaitable): it is awaited on the event loop that awaits `run_async`, or, under `run`, on a loop of the call's own; it never starts once its call has been answered, and is cancelled when its call ends. Excludes `host`.
- `gate`: Called with a `ToolCall` before each tool runs. It allows by returning `None` or `True`, and refuses by returning `False` or raising `ToolDenied`. It may be async, as a tool may. Needs `tools`.
- `max_tool_calls`: The most tool-protocol frames a call answers; the guest gets `ToolBudgetExceeded` for the rest. Default: `defaults().tool_calls`, 1,000. `None` means no limit. Needs `tools`.
- `max_tool_request_bytes`: The most bytes of tool-protocol requests a call reads, counted from each frame's length before it is read, whatever its answer; a frame that would pass it is refused unread, and the guest gets `ToolBudgetExceeded` and runs on. Default: `defaults().tool_request_bytes`, 16 MiB. `None` means no limit. Needs `tools`.

**Raises:**

- `TypeError`: An argument has the wrong type; raised before any work.
- `ValueError`: An argument is out of range; raised before any work.
- `ArtifactsMissing`: There is no usable artifact set.
- `ImportError`: wasmtime-py cannot load; its own error is chained as the cause.
- `OSError`: A host filesystem call failed while the root, the private folders, the zip's copy or the cache was prepared (its subclasses, such as FileExistsError, included).
- `RuntimeError`: This process was forked after it ran a guest; or a folder or the zip's copy changed between the runner's check and its use.
- `wasmtime.WasmtimeError`: Today, for a folder removed between the runner's check and wasmtime's own open. The type is wasmtime-py's and is not promised.
- `KeyboardInterrupt`: Ctrl-C.
- `BaseException`: One that is not an `Exception`, raised by your own host, provider, tool or gate, propagates.

#### `wasi_python.run_async`

```python
async def run_async(
    argv: Iterable[str],
    *,
    root: str | os.PathLike[str] | bool | None = False,
    grants: Iterable[Grant] = (),
    mounts: Iterable[Mount] = (),
    import_path: Iterable[str] = (),
    env: Mapping[str, str] | None = None,
    stdin: bytes | bytearray | memoryview | None = None,
    host: Callable[[bytes], bytes | bytearray | memoryview] | None = None,
    snapshot: bool = True,
    fuel: int | None = None,
    deadline_s: float | None = <default>,
    memory_bytes: int | None = <default>,
    output_bytes: int | None = <default>,
    cache_dir: str | os.PathLike[str] | None | bool = None,
    artifacts: Artifacts | None = None,
    executor: concurrent.futures.Executor | None = None,
    max_file_calls: int | None = <default>,
    tools: Iterable[Tool | Callable[..., Any]] | None = None,
    gate: Callable[[ToolCall], Any] | None = None,
    max_tool_calls: int | None = <default>,
    max_tool_request_bytes: int | None = <default>,
) -> Completed
```

`run` from async code, on a worker thread, so the event loop is never blocked.

`run`'s arguments except `cancel`, plus:

- `executor`: Where the call runs: a `concurrent.futures.Executor` that runs callables on threads of this process (a process or interpreter pool is refused). `None` (the default) uses the runner's own pool of `defaults().async_workers` threads.

**Raises:**

- `TypeError`: An argument has the wrong type; raised before any work.
- `ValueError`: An argument is out of range; raised before any work.
- `ArtifactsMissing`: There is no usable artifact set.
- `ImportError`: wasmtime-py cannot load; its own error is chained as the cause.
- `OSError`: A host filesystem call failed while the root, the private folders, the zip's copy or the cache was prepared (its subclasses, such as FileExistsError, included).
- `RuntimeError`: This process was forked after it ran a guest; the interpreter is shutting down; or a folder or the zip's copy changed between the runner's check and its use.
- `wasmtime.WasmtimeError`: Today, for a folder removed between the runner's check and wasmtime's own open. The type is wasmtime-py's and is not promised.
- `asyncio.CancelledError`: The awaiting task was cancelled; the guest was stopped and its worker freed first.
- `BaseException`: One that is not an `Exception`, raised by your own host, provider, tool or gate, propagates.

#### `wasi_python.set_defaults`

```python
def set_defaults(new: Defaults) -> Defaults
```

Replace the `Defaults` that calls read, and return the previous ones.

**Args:**

- `new`: The limits calls read from now on, already checked by `Defaults`.

**Raises:**

- `TypeError`: `new` is not a `Defaults`.

#### `wasi_python.stats`

```python
def stats() -> dict[str, int]
```

Counts kept by this process, a diagnostic.

### `wasi_python.tools`

#### `wasi_python.tools.PROTOCOL`

```python
PROTOCOL = 1
```

`PROTOCOL` is the number of the protocol this host speaks. The rules for its frames, the schema subset and the bounds are the protocol's own, not the host Python's, so an answer is the same on every host; they change only with `PROTOCOL` (README.md, "The tool protocol").

#### `wasi_python.tools.Tool`

```python
@dataclass(frozen=True, eq=False)
class Tool:
    name: str
    description: str
    fn: Callable[..., Any]
    validates_input: bool = False
    timeout_s: float | None = None
    read_only: bool = False
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False
    @property
    def input_schema(self) -> dict
    @property
    def output_schema(self) -> dict | None
    def descriptor(self) -> dict
    def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any
```

A host function offered to the guest, made only by `tool()`. Immutable; compared and hashed by identity. Calling it calls the function.

**Attributes:**

- `name`: The name the guest calls it by.
- `description`: What the guest is told it does.
- `fn`: The function it calls.
- `validates_input`: Whether schema keywords outside the protocol's subset are let through, unchecked, for a tool that checks its own input.
- `timeout_s`: The longest one call may run, in seconds; `None` for no bound beyond the run's own.
- `read_only`: A label shown to the guest as MCP's readOnlyHint; it grants nothing.
- `destructive`: A label shown as MCP's destructiveHint; it grants nothing.
- `idempotent`: A label shown as MCP's idempotentHint; it grants nothing.
- `open_world`: A label shown as MCP's openWorldHint; it grants nothing.

**Methods:**

- `Tool.input_schema`: A copy of the vetted input schema.
- `Tool.output_schema`: A copy of the output schema, or None. It is shown, never validated.
- `Tool.descriptor`: The tool in MCP's field names: name, description, inputSchema, and outputSchema and annotations when there are any. A fresh copy each time.
- `Tool.__call__`: Call the function with these arguments, on this thread, unchecked.

#### `wasi_python.tools.ToolCall`

```python
@dataclass(frozen=True)
class ToolCall:
    seq: int
    tool: Tool
    arguments: dict[str, Any]
    request_bytes: int
```

What a gate sees of one tool call.

**Attributes:**

- `seq`: The frame's number in this call, from 1.
- `tool`: The tool the guest called.
- `arguments`: A deep copy of the validated and decoded arguments; the tool gets its own.
- `request_bytes`: The frame's length in bytes.

#### `wasi_python.tools.ToolDenied`

```python
class ToolDenied(ToolError):
    ...
```

Raised by a gate or a capability to refuse a call; its message crosses (`denied`).

#### `wasi_python.tools.ToolError`

```python
class ToolError(Exception):
    ...
```

Raised by a tool to fail with a message the guest reads (`tool_error`), or by a gate to refuse with one (`denied`). Any other exception crosses only as "(internal error)".

#### `wasi_python.tools.ToolOutcome`

```python
@dataclass(frozen=True)
class ToolOutcome:
    seq: int
    op: str | None
    tool: str | None
    outcome: str
    message: str | None
    request_bytes: int
    response_bytes: int
    fault: str | None = None
    abandoned: bool = False
```

One frame, as the record lists it. Nothing in it measures time.

**Attributes:**

- `seq`: The frame's number in this call, from 1.
- `op`: "list", "call", or `None` when the frame was not read.
- `tool`: The tool's name, or the name the guest gave, cut to 64 characters.
- `outcome`: "ok", or one of the protocol's kinds of failure (README.md, "The tool protocol").
- `message`: What the guest was told on a failure.
- `request_bytes`: The frame's length in bytes.
- `response_bytes`: The answer's length in bytes.
- `fault`: An exception not meant for the guest: its type and first line.
- `abandoned`: Whether the tool still ran when the guest was answered.

#### `wasi_python.tools.ToolRecord`

```python
@dataclass(frozen=True)
class ToolRecord:
    frames: int
    outcomes: tuple[ToolOutcome, ...]
    unlisted: int
    abandoned: int = 0
```

Every frame of one call counted, the first 1,000 listed.

**Attributes:**

- `frames`: Every frame the guest sent.
- `outcomes`: The first 1,000 frames, each a `ToolOutcome`.
- `unlisted`: How many frames are counted but not listed.
- `abandoned`: Every call answered while its tool ran on, listed or not, so a guest cannot hide a tool still running with your authority behind 1,000 cheap frames.

#### `wasi_python.tools.stubs`

```python
def stubs(tools: Iterable[Tool | Callable[..., Any]]) -> str
```

Python stubs for a prompt: each tool as a `def` with the signature and docstring the guest's function carries, under a first line `from host import tools`.

**Args:**

- `tools`: The tools, each a `Tool` or a plain function, which goes through `tool()`.

**Raises:**

- `TypeError`: A plain function `tool()` refuses.
- `ValueError`: A plain function `tool()` refuses.

#### `wasi_python.tools.tool`

```python
def tool(
    fn: Callable[..., Any] | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: Any = None,
    validates_input: bool = False,
    timeout_s: float | None = None,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> Any
@overload
def tool(
    fn: Callable[..., Any],
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: Any = None,
    validates_input: bool = False,
    timeout_s: float | None = None,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> Tool
@overload
def tool(
    fn: None = None,
    /,
    *,
    name: str | None = None,
    description: str | None = None,
    input_schema: Any = None,
    validates_input: bool = False,
    timeout_s: float | None = None,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> Callable[[Callable[..., Any]], Tool]
```

Describe a function as a tool: `@tool`, `@tool(...)` with arguments, or `tool(fn, ...)`.

**Args:**

- `fn`: The function. Without it, `tool(...)` returns a decorator.
- `name`: The name the guest calls it by; by default the function's own.
- `description`: What the guest is told it does; by default the docstring up to its first section heading.
- `input_schema`: The input schema instead of the derived one: a dict whose root is an object, or anything with `model_json_schema()`.
- `validates_input`: Let schema keywords outside the protocol's subset through, unchecked, for a tool that checks its own input.
- `timeout_s`: The longest one call may run, in seconds; `None` for no bound beyond the run's own.
- `read_only`: Shown to the guest as MCP's readOnlyHint.
- `destructive`: Shown to the guest as MCP's destructiveHint.
- `idempotent`: Shown to the guest as MCP's idempotentHint.
- `open_world`: Shown to the guest as MCP's openWorldHint.

**Raises:**

- `TypeError`: An argument has the wrong type, the function is an async generator function, or a type hint has no schema.
- `ValueError`: A name or a schema the protocol does not allow.

### The command

`wasi-python run [OPTIONS] [--] ARG...` (also `python -m wasi_python`):

| option | value | action |
|---|---|---|
| `--env` | `KEY[=VALUE]` | append |
| `--stdin` | `PATH` | store |
| `--deadline-s` | `SECONDS` | store |
| `--memory-bytes` | `BYTES` | store |
| `--output-bytes` | `BYTES` | store |
| `--fuel` | `N` | store |
| `--no-snapshot` |  | store_true |
| `--grant` | `GUEST=HOST` | append |
| `--grant-writable` | `GUEST=HOST` | append |
| `--import-path` | `GUEST` | append |
| `--root` | `HOST` | once |
| `--private-root` |  | store_true |
| `--no-root` |  | store_true |

Exit codes: 0, a result; 1, run raised; 2, a usage error; 130, interrupted.

One line of JSON: on a result, `exit_code`, `fuel_used`, `stderr`, `stderr_base64`, `stdout`, `stdout_base64`, `trapped`, `truncated` (a stream that is not UTF-8 comes as its `_base64` key); on exit 1, `error`, `kind`.

<!-- api reference: end -->

## Safety

Made for running code nobody reviewed, such as a model's. The policy:
code planted in a root never runs at start-up or on import in a later call,
on either binary; data planted in a root a caller reuses is read by later
calls, and only a fresh root closes that; a call that names no limit still
has one.

**Enforced, and judged** (`tests/checks/test_v1_2_*.py`):

- the guest sees only its root: no host path, no `..` out, and the guest
  cannot follow a symbolic link out (refused on open). It can still
  *create* a relative link that points out, which matters to host code that
  reads its root afterwards (see "Not protected");
- no network, no processes, no shared libraries; two imports only, WASI
  preview1 and the one door;
- only the stdlib zip and the read-only entries the embedder names are on the
  import path; each is served by a read-only grant, and no folder the same
  call's root or grants can write lies under one (a hard link, a writable
  mount whose store is an entry's folder, and other calls are yours to keep
  apart: see *The import path*). `site`
  does not run, so modules, `.pth` files or a `pyvenv.cfg` planted in a root
  never run
  (`sys.flags.no_site` is 1; `exit`, `quit`, `help` and `license` exist
  as in native Python);
- every door frame is bounded by guest memory, and nothing a frame or a
  host function does makes `run` raise;
- the deadline holds while the guest waits: the runner answers
  `poll_oneoff` itself (`time.sleep`, `select`), in slices that stop at the
  deadline, as wasmtime answers it except as spec 010 states (a directory or
  an unopened descriptor is reported ready; a bad pointer answers `EFAULT`);
  more than 4,096 subscriptions answer `ENOMEM` (`select.poll()` on more than
  2,047 descriptors with its default mask);
- **defaults** (`wasi_python.defaults()`): 1 GiB of memory, a 60 s
  deadline, 16 MiB of output per stream (the rest dropped and named in
  `truncated`); pass `None` for no limit. A limit of the wrong type or out
  of range (a negative cap, `True`, a deadline of 0) raises `TypeError` or
  `ValueError` before any work, so no value can quietly remove a limit;
  integer limits take any integer type (numpy's included) from 0 to
  2**63 - 1, and a deadline is a positive real number of seconds, counted in
  ticks of 10 ms (any positive deadline is at least one tick). The
  guest's environment starts from `TMPDIR=/tmp`, `PYTHONTZPATH=`
  (`zoneinfo` on the zip's tzdata) and
  a `HOME` made fresh and empty for each call in the folder the guest sees at
  `/tmp` and removed after it (no `HOME` where there is none); `env=` is laid
  over them;
- **grants** are read-only unless they say otherwise, checked before any
  work, and checked again after wasmtime opens them (see *Grants*); the stdlib
  zip is a read-only grant on every call;
- **mounts** (see *Mounts*) are read-only unless you pass `writable=True`,
  your explicit grant of a write channel into your own code; a provider is
  your code, called only with normalized paths, after the runner has checked
  every pointer, length and count the guest passed; offsets, flags, cookies
  and descriptors stop in the runner. No host path is opened for a mount:
  each mount, writable or not, is preopened on an empty, read-only folder the
  runner owns, inside the call's private folder, and every write is served
  from the runner's buffer or your provider, so nothing a guest writes
  reaches a host file through a mount; a call without mounts runs on
  wasmtime's own calls but for the two the runner guards (next item). Nothing
  a provider raises or answers makes `run` raise (a `BaseException` that is
  not an `Exception` is raised, as a door host's is); provider calls, open
  files and staged bytes each have a default limit;
- **two wasmtime fixes the pinned wasmtime-py lacks** (spec 048): no wasmtime-py
  release yet carries a wasmtime past 49.0.0, so the runner serves two
  preview1 calls itself, on every call, and forwards them to wasmtime with the
  fixes of wasmtime 49.0.2 and 49.0.3. A rename with a trailing `/` on either
  path needs a source that is a folder, judged without following the source's
  own link (`ENOTDIR` for a file or a link), and a folder is renamed by its
  plain name: on macOS and FreeBSD wasmtime 49.0.0 lets a guest with a writable
  grant or root rename a link that points out with a trailing slash and so
  move a host folder into its sandbox (GHSA-m9f7-9w4p-gv38). Every
  `fd_readdir` entry's padding is zeroed, where wasmtime 49.0.0 copies up to
  three bytes of host memory (GHSA-96f6-r43r-8c24). Both cost no fuel, and each
  goes once the published `wasmtime` requirement admits only fixed versions.
  The fixes are in this package's runner, not in the artifact set: an
  embedder that drives the artifacts with its own wasmtime before 49.0.3
  does not get them;
- **inputs**: `argv` is any iterable of `str`, `env` a mapping of `str` to
  `str`, `stdin` a bytes-like object. One the guest would see differently
  (a NUL, text that is not UTF-8, an `=` or nothing as an env key) raises
  `ValueError` before any work, and a wrong type `TypeError`; no message
  quotes a value;
- each call's store is closed when it ends, trapped or not, so its memory
  and open files are released at once; a process copies the 11 MB stdlib
  zip once, into a folder of its own that its exit removes;
- calls made through `run` share nothing with each other but the stdlib
  zip's folder, which each sees read-only: the host
  functions are defined once per engine and serve only the call whose store
  called them, and each call's output goes to its own buffer, never through
  wasmtime-py's shared callback tables; whatever a host function catches (a
  trap in the guest's allocator, a host's `SystemExit` or `CancelledError`,
  Ctrl-C) stops that call and is reported or raised by that call's `run`, on
  its own thread. While `run` holds the main thread under Python's default
  SIGINT handler, Ctrl-C ends the call at the guest's next wait or door
  call, or during a wait, or else at its deadline; an embedder's own
  handler is left alone.

To report a way around any of this, see [SECURITY.md](SECURITY.md).

**Not protected:** a killed process (mid-call, its private root and stdin
folder; at any time after its first call, its 11 MB stdlib zip folder; each
with its lock file, stay in the temporary folder until another
process using wasi_python on the same kernel, with the same temporary
folder, starts its first call; folders from releases before 0.1.0a3 have no
lock file and are never removed: delete `wasi-python-*` entries there by hand
when no wasi_python process runs; two machines that share one temporary
folder and report the same identity, such as cloned Windows images, are not
told apart; a temporary folder on a filesystem without file locks, where such
folders are never removed); disk use in any
root, the private one included (a guest
can write as fast as the disk takes it until its deadline, tens of GiB in
the default 60 s; point `tempfile.tempdir`, or `root`, at a size-limited
volume if that matters); links a guest leaves in a granted root that point
outside it (host code that reads or writes the root after a call must not
follow links: open with `O_NOFOLLOW`, or check `os.lstat` first);
the host's file
descriptors (a guest can hold thousands of open files, which the embedder's
process shares; wasmtime-py offers no lower limit; while one guest holds them
all, the embedder's own code and other calls' `run` can fail with `OSError`,
though that guest's own call ends cleanly); data planted in a
reused root (dateutil's zone files, `mimetypes`' tables, any user file, the
plain reactor's `sys.prefix` after a planted `pyvenv.cfg`); pdb's `./.pdbrc`
in the current directory, `/`, which pdb runs as code when a program starts
pdb, as native pdb does (a fresh root closes it); a script or module the caller names to run
from a reused root; an lxml XSLT stylesheet given no `access_control`, or a document it loads,
which can read any file in the call's grants, external entities included, and write into its
writable grants (use `XSLTAccessControl.DENY_ALL`; see *lxml in the guest*); concurrent calls on one root, or a guest that can write a folder above
another call's root (it can hard-link or change the files that call uses,
and make that call's `run` raise `ValueError`, `RuntimeError`,
`WasmtimeError` or `OSError`; nothing outside the grants changes); a guest that waits
(`time.sleep`, `select`) in a call with `deadline_s=None`, which waits as
long as it asks (no instruction runs, so fuel does not stop it); Ctrl-C
for a guest that never waits or calls the door in a call with
`deadline_s=None` and no `cancel` (it runs on; with `cancel=`, the runner's
check ends it); Ctrl-C under an embedder's SIGINT handler
that raises, asyncio's on a second Ctrl-C included, while a guest runs on
the main thread: wasmtime-py, or under `cancel=` the runner's epoch
callback, can then abort the process, so call `run` on a worker thread
(`run_async`, `asyncio.to_thread`, a thread pool) there; other code in the
same process using wasmtime-py directly, whose exceptions can reach a
trapping `run` through wasmtime-py's shared exception slot; an `env=` that
overrides `HOME` or `PYTHONTZPATH` on a reused root (pdb then reads a
`.pdbrc`, and `zoneinfo` a zone file, that a guest may have planted there);
`stdin`, which is written to a host temporary file of its size; SQLite's own
randomness (`random()`, `randomblob()`, its temporary names), which is seeded
from the clock's whole second because the guest has no `/dev/urandom`, so two
calls in the same second repeat it and a `/dev/urandom` planted in a reused
root sets it (Python's `random`, `secrets`, `os.urandom` and `tempfile` names
use real entropy); a stale SQLite lock and hot journal left in a reused root
by a guest stopped inside a transaction (see *sqlite3 in the guest*); an `argv`
or `env` larger than the guest's memory, which exits 1 with empty stderr;
host CPU spent on tool frames, within two limits: their parsing by the
request-byte budget (16 MiB by default), and each frame's fixed cost and each
`list` answer's copy by `max_tool_calls` (1,000 by default); with a limit set
to `None`, the deadline bounds what it bounded (see *Tools*, "The host's cost
per frame"); timing
(the clock is real and fine-grained); real entropy; the one-byte exit status.

## Scope

**In the first release:** CPython, numpy, pandas, zlib, python-dateutil,
tzdata, six, the host door, the snapshot. **Since then:** `sqlite3`, `bz2` and
`lzma` (SQLite 3.54.1, bzip2 1.0.8, liblzma from xz 5.8.4); matplotlib 3.11.2's
first milestone (spec 023: line plots and PNG, PDF, PS and SVG saves on Agg, with
FreeType 2.14.3, HarfBuzz 14.1.0, SheenBidi 3.0.0, libraqm 0.10.5, Pillow 13.0.0's core
with zlib only, kiwisolver 1.5.1, fontTools 4.67.0, cycler, pyparsing and packaging).

**Out, with the one fact that decides each:** matplotlib's Delaunay triangulation
(`_qhull` needs a second carried patch, for a writable `/dev/null`) and `contour`
(contourpy's own build), both its next milestone; pre-importing matplotlib in the snapshot
(the owner's question 34); scipy (Fortran: f2c as Pyodide does; months);
threads; BLAS and SIMD; `_ctypes`, `mmap`, sockets, `_ssl`; `_zstd`
(`compression.zstd`: libzstd needs its own research and licence approval);
SQLite's `load_extension` (WASI has no `dlopen`); pip inside the guest.

## Next

In order. Each item is a specification or a research memo under
`context/`; `uv run pytest` names what blocks the most checks (its `next:`
line). The runner, the door, the reactor, the build, the release workflow
and the 3.15 line have landed (specs 001, 003, 004 and 005). The direction
past these is in
`context/research/2026-10-16-a-principal-engineers-direction.md`.

1. numpy's and pandas' own test subsets under the runtime: judged since spec 050.

Decided already, without further study: both binaries ship, the snapshot
first; the stdlib zip is bytecode-only and deflated; the int32 default
integer is documented, not patched.

## How this repo is organized

- `recipes/`, `scripts/`, `fixtures/`, `downloads/SHA256SUMS`: the build.
- `src/wasi_python/`: the wheel. `tests/`: its tests and the progress
  harness; `uv run pytest` prints the v1 scoreboard and guards it with a
  ratchet (`context/progress/README.md`), and `uv run pytest -n 6` gives
  the same answer on six cores.
- `context/`: the project's memory. `prior_art/` holds shallow clones we
  study and never copy (git-ignored, indexed in its README); `research/`
  holds dated memos, executed or marked placeholder; `specifications/`
  holds numbered work packages; `reviews/` holds the review of each built
  change before it lands. See `context/README.md`.
- `AGENTS.md`: the rules an agent follows here.

## Evidence

`context/research/2026-10-16-the-spike-that-proved-the-build.md` is the
executed spike this project grew from: every command, every number.
Its outputs, logs and generated link lines are in
`context/research/2026-10-16-the-spike-that-proved-the-build/`, and
`context/research/2026-10-16-the-spike-evidence-in-this-repository.md`
maps the spike's paths to this repository's. The spike ran inside
another repository, the first consumer of this runtime; nothing here
needs it.

## Why WASI and not "wasm"

WebAssembly is the machine: an instruction set and a file format. WASI is
the operating system interface the binary talks to: files, clock, args,
stdout. This binary needs a WASI host and nothing else. "Python in wasm"
usually means Pyodide, which needs a browser or Node through Emscripten's
JavaScript glue. This is the other thing.
