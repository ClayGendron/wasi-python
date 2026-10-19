# wasmtime's errnos for a read-only grant, a trailing slash, and Windows hosts' file rules

- **Found** by spec 065's research (`context/research/2026-10-18-cpythons-own-tests-under-the-runtime.md`,
  section 4.4) running CPython's own tests in wasm32-wasip1 under wasmtime 49 (wasmtime-py
  49.0.0), and checked again while drafting spec 065 (EXECUTED, both of this project's binaries,
  on darwin-arm64; `context/research/2026-10-18-cpythons-own-tests-under-the-runtime/evidence/spec-065-drafting/probe_c.py`).
  Nothing is posted: the owner decides whether to report it to wasmtime. Whether each answer is
  wasmtime's choice or the WASI specification's is not checked.
- **1. A read-only grant answers `EPERM` before it checks that a path exists.** In the guest,
  `os.unlink("/usr/local/lib/nonexistent.pyc")`, where `/usr/local/lib` is a read-only grant,
  raises `PermissionError: [Errno 63] Operation not permitted`. Under a writable grant the same
  call raises `FileNotFoundError` (`[Errno 44]`), and natively `FileNotFoundError`. Code written as
  `try: os.remove(p) except FileNotFoundError: pass` breaks under a read-only grant: CPython's
  `test.support.forget()` does exactly that for every `sys.path` entry, which fails 21 of CPython's
  tests and leaves `sys.path` altered in `test_doctest` and `test_bdb`.
  - Reproducer: grant a folder read-only, then `python -c "import os; os.unlink('/<grant>/missing')"`.
- **2. A trailing slash on a missing path gives `EINVAL`.** `open("/tmp/nope/", "wb")` raises
  `OSError: [Errno 28] Invalid argument` in the guest; natively `FileNotFoundError` (or
  `IsADirectoryError` on some hosts). CPython's `test_shutil.TestCopy.test_copyfile_nonexistent_dir`
  expects `FileNotFoundError`.
  - Reproducer: `python -c "open('/tmp/nope/', 'wb')"` in a writable root.
- **Host dependence** (EXECUTED, spec 065's branch dry runs 39192207869 and 39194284100, Linux
  x86-64 and Windows runners): item 1 gives the same answer on every host (its classes held on all
  three). Item 2 does not: `EINVAL` on darwin, `ENOENT` on Linux (the test passes there),
  `ENOTDIR` on Windows; spec 065 records it as the host entry `trailing-slash`.
- **3. A Windows host refuses to remove a file the guest holds open.** `tempfile.TemporaryFile`
  in the guest opens a file and unlinks it at once (the POSIX path: the guest's `os.name` is
  `posix`). On a Windows host that unlink fails with `EACCES` (`PermissionError: [Errno 2]`), or
  the file stays behind (`Directory not empty` later); 22 of CPython's `test_tempfile` tests
  differ there. darwin and Linux hosts remove it, as POSIX does.
- **4. A colon in a name** (`E:abspath`, from `test_shutil`'s bad-paths archive) cannot be made on
  a Windows host: `FileNotFoundError` where other hosts make the file.
- **5. Opening a folder for reading** gives `EINVAL` on a Windows host, `IsADirectoryError`
  elsewhere (`test_shutil.TestCopy.test_copyfile_copy_dir`).
- Items 3 to 5 are spec 065's 25 Windows host entries (`win-*` in `tests/upstream/python.toml`),
  each recorded per system, so the release's verdict is one on every host. They close with the
  README's *On Windows* list, which states them as a Windows grant's rules.
- **What this project does meanwhile:** the README states both facts; spec 065's classes
  `read-only-eperm` and `trailing-slash-einval`, and its environment entries `sys-path-doctest` and
  `sys-path-bdb`, name this sheet as their closer.
