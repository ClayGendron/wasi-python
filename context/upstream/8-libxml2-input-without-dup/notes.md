# How the libxml2 `dup()` change was found and checked

- **Found** while drafting spec 046 (2026-10-18). The default-profile memo
  (`context/research/2026-10-17-what-else-the-default-profile-carries.md`, the native-extensions
  table) named "`dup()` in libxml2 (patch or recipe)" from its reading of HubSpot's boomslang,
  which builds libxml2 for `wasm32-wasip1` with a change of its own
  (`context/prior_art/boomslang/cpython/lxml-wasi/libxml2-wasi-no-dup.patch`, Apache-2.0,
  studied, not copied). This change was written from libxml2's own source: it reuses libxml2's
  `xmlFdFree` instead of adding a function, and covers standard output as well.
- **A recipe was weighed first** (§4.1 prefers one), and one is possible. WASI preview 1 cannot
  copy a descriptor, so a stand-in `dup` alone would either fail (and every file read by name
  with it) or return the same number, which the opener closes at once. But a forced-include
  header for `xmlIO.c` alone that maps both `dup` and `close` to a small reference-counting pair
  compiles the pristine file without a warning and would give the same ownership at all three
  sites (the spec review's `shim/` sketch, compiled, not run). **Why the patch anyway:** that
  header changes what two libc calls mean inside upstream's file without one line of the file
  showing it, so a reader of `xmlIO.c` and a reviewer of the patch list both miss it, and it
  adds descriptor bookkeeping of our own that upstream will never carry or test. The patch is
  the same size, is visible in `recipes/patches/`, says what it does in libxml2's own terms
  (reusing `xmlFdFree`), can go upstream as it is, and is deleted when upstream takes it. This
  is the reasoning spec 043's review accepted for its forced headers.
- **Seen failing first:** `make libxml2.la` on the pristine 2.15.4 tree stops on two `dup`
  calls (`evidence/unpatched-build.txt`). With `fix.patch` applied the build gives no warning
  (the first draft left `copy` unused on WASI, one warning; the change now assigns it).
- **Checked** (EXECUTED 2026-10-18): `evidence/lxml_probe.py` run natively (CPython 3.15.0, the
  lxml 6.1.3 macOS universal2 wheel, which bundles libxml2 2.14.6 and libxslt 1.1.43) and in a
  scratch guest built with this change (`evidence/native.txt`, `evidence/guest.txt`). Every file
  read and write equals native. The other differences in the two outputs are not this change's:
  the library versions; libxml2 2.15's HTML `<meta charset>` serialization; GB2312 and Big5
  output, which wasi-libc's iconv does not encode (`evidence/encodings.txt`); paths that differ
  in length between the host and the guest; and three things spec 046 records (no zlib in the
  guest's libxml2, `lxml.isoschematron` reading its resources by path, python-docx's template
  read by path).
- **Tests upstream.** libxml2's CI has no WASI job. On every other platform the change compiles
  the current code, so its existing tests cover it there.
