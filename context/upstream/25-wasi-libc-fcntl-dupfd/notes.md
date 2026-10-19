# How wasi-libc's fcntl and dup disagreement was found and checked

- **Found** by spec 086's trial (2026-10-19): with the pin moved to wasi-sdk 34, numpy-core's
  upstream group turned red. Its eight `tofile`/`fromfile` tests failed with `[Errno 28] Invalid
  argument` where its `no-dup` class expects `[Errno 58] Not supported`. The counts and the pass
  digest were unchanged (9,519 passed, `df21e78e7032`).
- **Located** (2026-10-19): CPython 3.15.0's `Python/fileutils.c` (`_Py_dup`, its
  `F_DUPFD_CLOEXEC` branch before `HAVE_DUP`), read in the build's own source tree; wasi-libc
  `2e6fb9d8`'s `libc-bottom-half/cloudlibc/src/libc/fcntl/fcntl.c` and
  `libc-bottom-half/sources/dup.c`, fetched by `raw.githubusercontent.com` URL into a scratch
  folder and read. No wasi-libc code is stored in this repository. Spec 086's pre-build review
  read the same files and agreed (its section 3).
- **Checked** (EXECUTED): the guest's `os.dup(1)` errno with and without the recipe's wrap, and
  numpy-core's group with it (passes, its classes matching). Spec 086's check
  `test_dup_is_refused_as_not_supported` holds the answer.
- **Not run:** a wasi-libc rebuilt with the fix (none was built).
- **README row, for when this lands** (for `context/upstream/README.md`'s table):
  `| 25-wasi-libc-fcntl-dupfd/ | wasi-libc | on wasip1 the header defines F_DUPFD and F_DUPFD_CLOEXEC, but fcntl answers them EINVAL while dup answers ENOTSUP | a facts sheet; spec 086 answers them ENOTSUP by a recipe until a wasi-sdk carries the fix |`
