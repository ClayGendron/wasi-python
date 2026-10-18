- **Project:** libxml2 (https://gitlab.gnome.org/GNOME/libxml2)
- **Against:** 2.15.4 (the pinned tarball)
- **Status:** drafted
- **Title:** xmlIO: read and write files without dup() on WASI
- **Files:** xmlIO.c
- **Why we carry it:** libxml2 2.15.4 does not compile for `wasm32-wasip1` (wasi-libc declares no `dup`, so clang stops on `xmlIO.c`), and without a `dup` every file libxml2 opens by name (`etree.parse(path)`, XInclude, a DTD, XSLT's `document()`) would fail in the guest.

**This is a facts sheet, not a merge request** (question 80 in
`context/questions-for-the-owner.md`). libxml2's tree carries no contributor guide and no rule on
AI-written changes that the agent could find (READ: the 2.15.4 tarball, and `README.md` on
`master`, 2026-10-18; a `CONTRIBUTING.md` there does not exist). Under question 80's
recommendation, if you send it, you write the issue or merge request yourself from these facts.
Nothing has been posted, and no agent will post anything to libxml2.

When spec 046 is built, this file moves unchanged to
`context/upstream/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.md`, and `fix.patch` is
copied byte for byte to `recipes/patches/libxml2-2.15.4/0001-xmlio-without-dup-on-wasi.patch`.
The evidence stays in `context/upstream/8-libxml2-input-without-dup/evidence/`, so every link
below is a path from the repository's top.

## What libxml2 asks of a change

READ, 2026-10-18: the project takes merge requests and issues on GNOME's GitLab
(`README.md`: "Bugs should be reported at https://gitlab.gnome.org/GNOME/libxml2/-/issues").
Its README says contributions are welcome and asks people to be kind and not to pressure the
volunteers. No contributor licence agreement is named; the code is MIT (`Copyright`), and this
change is new code under the same terms.

**Checked for you** (2026-10-18): `xmlIO.c` on `master` still calls `dup` in the same three
places (lines 1206, 1238 and 1272 of the file fetched from
`https://gitlab.gnome.org/GNOME/libxml2/-/raw/master/xmlIO.c`), with no `__wasi__` branch.

## The facts

**What fails.** WASI preview 1 has no call that duplicates a file descriptor, and wasi-libc
declares `dup` only under `__wasilibc_unmodified_upstream` (its `unistd.h`, line 54). So a
`wasm32-wasip1` build of 2.15.4 stops at compile time
(`context/upstream/8-libxml2-input-without-dup/evidence/unpatched-build.txt`):

```
xmlIO.c:1230:12: error: call to undeclared function 'dup'; ISO C99 and later do not support implicit function declarations
xmlIO.c:1264:14: error: call to undeclared function 'dup'; ...
```

The third call (line 1198) sits in the zlib branch and is compiled only `--with-zlib`.

**Why libxml2 duplicates at all.** `xmlInputFromFd` reads from a descriptor its caller owns,
and the buffer's close callback (`xmlFdClose`) closes what it reads from; the copy lets the
buffer close its own descriptor. The default file opener (`xmlParserInputBufferCreateUrl`)
opens a file, hands the descriptor to `xmlInputFromFd`, and closes its original at once.
`xmlOutputDefaultOpen("-")` duplicates standard output for the same reason.

**The change** (`fix.patch`, 40 lines added, 2 removed; every other platform compiles the
current code unchanged, in `#else` branches):

- `xmlInputFromFd` on WASI reads from the caller's descriptor itself and closes the buffer
  with `xmlFdFree`, which frees the context and leaves the descriptor open. That is the
  ownership every public caller already documents (the caller keeps and closes its `fd`).
- The default file opener on WASI, after a successful `xmlInputFromFd`, switches the buffer's
  close callback to `xmlFdClose`, so the buffer owns and closes the file it opened, instead
  of closing it straight away.
- `xmlOutputDefaultOpen("-")` on WASI writes to `STDOUT_FILENO` and closes the buffer with
  `xmlFdFree`, so standard output stays open.

**How it was tested** (EXECUTED 2026-10-18, in a scratch folder: libxml2 2.15.4 with this
change, built static for `wasm32-wasip1` by wasi-sdk 33's clang with `--without-threads
--without-modules --without-zlib --without-python --with-schematron` and `-DLIBXML_STATIC`;
libxslt 1.1.45; lxml 6.1.3; linked into this project's CPython 3.15 reactor and run under
wasmtime 49 with one read-only and one writable folder;
`context/upstream/8-libxml2-input-without-dup/evidence/guest.txt`, beside the same program
natively in `native.txt`):

- the build gives no warning;
- parsing a file by path, fifty times in a row, `iterparse` of a path, XInclude of a file, a
  DTD loaded by path and XSLT's `document()` on a file all give native lxml's results;
- a missing file raises lxml's `OSError` ("failed to load ... No such file or directory");
- writing to a path, and to `-` (standard output), give the native bytes, and standard output
  stays usable after the write.

**What it does not cover.** The change is for builds without zlib, which is ours (lxml falls
back to Python's `gzip` for compressed output). With `--with-zlib` on WASI two things remain:
the decompression branch of `xmlInputFromFd` still calls `dup` (it hands the copy to `gzdopen`,
which closes it), so the build still does not compile; and in `xmlOutputDefaultOpen`, the
compression branch would hand `STDOUT_FILENO` to `gzdopen` for `"-"`, whose `gzclose` closes
it, and that branch's failure path calls `close(fd)` whatever the `owned` flag says. The flag
covers only the uncompressed path. The 2.15 news lists zlib file I/O as a removal candidate; a
merge request may say so, or extend the flag to the compression branch.

**A form upstream may prefer.** The default opener could hand its descriptor to the buffer on
every platform, dropping one `dup` and one `close` per opened file; only `xmlInputFromFd`
(caller-owned descriptors) and `"-"` would keep `dup` where it exists. That is a wider change
than this project needs, and it was not built or tested here.
