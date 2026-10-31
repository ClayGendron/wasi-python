# Limitations

What does not work in the guest, or works differently from native Python, and why. Most of it follows from the platform: `wasm32-wasip1` is a 32-bit machine with WASI's system interface, which has no threads, no processes, no network and no shared libraries. The project documents these facts rather than patching them away. Each fact below has its reason beside it.

A known failure in a package's own test suite, or in one of the project's checks, points at a section of this page.

## The platform's facts

`python.wasm -V` prints them after its version:

> (wasm32-wasip1: numpy's default integer is 32-bit; no threads; no ctypes, mmap, sockets, ssl, zstd or scipy.odr; compute about 1.3 to 2.3 times slower than native)

- **numpy's default integer is 32-bit.** `wasm32`'s C `long` is 32 bits, and numpy's default integer follows it. So `np.arange(1_000_000).sum()` wraps; pass `dtype=np.int64`.
- **No threads.** `wasm32-wasip1` has no threads. Code that starts one fails, and nothing runs in parallel inside the guest.
- **No processes.** WASI has no `fork` or `exec`, so `subprocess` and `multiprocessing` cannot start anything.
- **No network.** The guest has no sockets. Data comes in through a grant, a mount, standard input or a host tool.
- **No `_ctypes`.** WASI has no `dlopen`, so no library can be loaded. `import ctypes` works: it sizes wasm32's C types and gives numpy their dtypes, but loading a library or calling through a pointer raises `OSError`.
- **No `mmap`.** WASI cannot map a file into memory. A memory map (joblib's `mmap_mode`, for one) raises `OSError`, and Pillow falls back to reading the file, silently. pandas' parallel `read_csv`, chosen by setting `mode.max_threads` above 1, maps its file and raises `OSError`; leave the option unset.
- **No `_ssl` and no `_zstd`.** There is no network for TLS to protect, and libzstd is not built.
- **No `scipy.odr`.** It needs ODRPACK, which is Fortran, and scipy has deprecated it for removal. `import scipy.odr` raises `ImportError` saying so.
- **No `dup`.** WASI cannot duplicate a descriptor. `os.dup`, `os.dup2` and `os.pipe2` exist and raise `OSError` (`ENOTSUP`); `os.pipe` is absent. `ndarray.tofile` and `np.fromfile` on real files fail for the same reason; use `tobytes()` and `np.frombuffer`, or `io.BytesIO`. `np.save` and `np.load` of paths and open files work.
- **No `resource` module.** WASI has no `getrusage` or `setrlimit`, so `import resource` raises `ModuleNotFoundError`.
- **No floating-point status flags.** WebAssembly arithmetic sets none, so what only the hardware signals stays silent: `np.array([1.0]) / 0`, `np.log(0.0)` and `np.sqrt(-1.0)` give native's values with no `RuntimeWarning`, and `np.errstate(all="raise")` does not raise for them. Check with `numpy.isfinite` where it matters. numpy's own software signals (integer division by zero, float16 overflow) warn and raise as natively.
- **No `/dev/null` and no permission bits.** `os.devnull` names a path that does not exist. `os.chmod` succeeds and changes nothing, and `st_mode` carries no permission bits.
- **Errors are WASI's numbers.** A missing path is `[Errno 44]` (`ENOENT`), where Linux says `[Errno 2]`. Under a read-only grant, removing a path raises `PermissionError` even when the path does not exist.
- **At most 4 GiB of memory.** wasm32 addresses 65,536 pages of 64 KiB. A request past that, or past the runner's `memory_bytes` limit, raises `MemoryError`. Linear algebra needs about 16 MiB more than the program holds: OpenBLAS maps a buffer at its first call, and if the limit leaves no room it ends the call with exit status 1 instead of raising.
- **Deep recursion stops earlier than native.** Recursion through Python code raises `RecursionError` after 40 to 250 levels, where native Python allows 1,000, because the guest's C stack is small. Recursion in C over nested data (`repr`, `==`, `hash`, `json` of deeply nested structures) raises too. A few deeper cases end the call with the trap "stack overflow", such as freeing a list nested more than about 32,000 deep. A trap ends only that call.
- **Builtin modules have no `__file__`.** The packages' compiled modules (numpy's, `lxml.etree`, `PIL._imaging`) are linked in, so code that reads their `__file__` fails.
- **Compute is slower than native.** numpy's own loops have no SIMD, and nothing runs on a second core; expect about 1.3 to 2.3 times native's time for numeric work.

## SQLite

`sqlite3` has native's feature set (FTS3/4/5, R-tree, Geopoly, math functions). WASI has no file locks, so SQLite uses its WASI default, a lock directory, and these facts follow from it:

- One connection holds the database, through a `<db>.lock` directory beside it, while it writes or has a statement open. A second connection then gets "database is locked" after its busy timeout.
- `journal_mode=wal` stays `delete`, unless the connection first sets `locking_mode=exclusive`.
- A guest stopped inside a transaction leaves `<db>.lock` and a hot journal. In a reused root, remove the lock directory and SQLite rolls the journal back. A call with `root=True` never sees a stale lock, since its root is fresh.
- A database in a read-only folder opens only through a URI that takes no lock, such as `file:<path>?immutable=1` with `uri=True`, because the lock is a directory made beside it.
- SQLite's own randomness (`random()`, temporary file names) is seeded from the time in whole seconds, since the guest has no `/dev/urandom`. Use `secrets`, `uuid.uuid4()` or `os.urandom` for identifiers.
- SQLite's math functions follow the guest's C library, so their last digits can differ from native's.
- No `load_extension`, since WASI has no `dlopen`. `sqlite3.threadsafety` is 0.
- sqlite3 over a mount is not supported: it needs ranged writes and locking.

## Packages that are not in the set

The set is fixed at build time. See [Packages](packages.md) for what it carries.

- **No `pip` in the guest.** Packages are compiled in or carried in the read-only stdlib zip; nothing is installed at run time. Pure-Python code of your own can be imported from a read-only grant through `import_path=`.
- **No pyarrow**, so no Parquet. CSV, JSON, Excel and pickle work.
- **No pytz.** `zoneinfo` reads the zip's tzdata instead.
- **No cryptography and no pypdfium2.** pypdf and pdfminer.six read files encrypted with RC4, and raise for one encrypted with AES. pdfplumber reads text and tables, but `page.to_image()` raises `ModuleNotFoundError`.
- **No predefined CJK character maps in pdfminer.six.** A font that names one of Adobe's CJK maps and has no ToUnicode table reads as `(cid:N)`. Most files carry a ToUnicode table and read normally.
- **No netCDF4, h5netcdf or zarr for xarray.** `to_netcdf()` and `open_dataset()` read and write netCDF3 through scipy; the other engines and `xarray.tutorial` raise as natively without their packages. scipy maps a netCDF3 file opened by path, and the guest has no `mmap`, so `open_dataset(path)` raises `OSError`: pass `mmap=False`, or an open file.
- **drawsvg writes SVG and HTML, not images.** Its PNG, GIF, video and sprite-sheet output (`rasterize`, `save_png`, `save_gif`, `save_mp4`, `save_spritesheet`) needs CairoSVG and imageio, and `drawsvg.color` needs pwkit; none is carried, so each raises `ImportError`. The message suggests `pip install`, which does not apply in the guest. `embed_google_font` raises `URLError: unknown url type: https`: the guest has no `ssl` module, so no HTTPS, and no network. `drawsvg.widgets` raises `ModuleNotFoundError` naming `ipywidgets`.
- **No `cssselect` and no `lxml_html_clean`**, so `lxml.cssselect` and `lxml.html.clean` raise lxml's own `ImportError`, as natively without them.
- **No SQLite extensions** (`load_extension`), as above.
- **Pillow has zlib and libjpeg-turbo, and none of its other codec libraries.** PNG and JPEG work, as do the formats Pillow reads itself, such as GIF, BMP and uncompressed TIFF. WebP, AVIF, JPEG 2000 and TIFF's compressions raise an error.
- **No C extension of your own.** A compiled module must be linked into `python.wasm` when it is built; the guest cannot load one.

## On Windows

A writable grant answers as Windows does; a mount answers the same on every host.

- `os.rename` of a folder onto a file replaces the file on a Windows grant. A mount never does, and answers `ENOTDIR`, as a Linux or macOS grant does.
- A Windows grant cannot remove or rename a file the guest holds open, so `tempfile.TemporaryFile` and an `os.replace` inside a `NamedTemporaryFile`'s `with` fail there. A mount allows both.
- A mount refuses a name with a backslash or a colon with `EINVAL` on every host, so a guest cannot name a file such as `12:30.csv` on a mount, where it can on a Linux or macOS grant.
- A Windows grant cannot make a name with a colon, and opening a folder for reading there gives `OSError` `EINVAL` where other hosts give `IsADirectoryError`.
- Opening a missing path with a trailing slash raises `NotADirectoryError` on Windows, `FileNotFoundError` on Linux and `OSError` `EINVAL` on macOS.
- A guest with a writable grant or a private root can delete a file the host gave the read-only attribute.

## What the stdlib zip means

The standard library and the packages' Python code are bytecode in one read-only zip, `python-stdlib.zip`, seen by the guest at `/usr/local/lib/python315.zip`. That keeps the set small and the start fast, and it has these consequences:

- Tracebacks into the stdlib show no source line. `inspect.getsource`, `linecache`, `pdb` and `pydoc` have no source for it.
- `os.path.exists` of a stdlib module's `__file__` is false, and the zip's path cannot be listed.
- Tracebacks and warnings name a module by its full zip path, such as `/usr/local/lib/python315.zip/pandas/core/frame.py`.
- `importlib.metadata` gives each package's name, version and entry points, and `packages_distributions()` maps each import name to its package. `files()` gives `None`, because the zip keeps no `RECORD`.
- `importlib.resources.files()` on a package in the zip gives the runtime's own reader, not a `zipfile.Path`. It lacks `root`, `at`, `glob`, `rglob` and a few more of `zipfile.Path`'s members.
- The packages' own `tests` folders are not in the zip.
- The snapshot runs only beside the exact stdlib zip it was built against, because zipimport's file offsets are part of the snapshot.

See also [Troubleshooting](../how-to/troubleshooting.md) and [The security model](../explanation/security-model.md).
