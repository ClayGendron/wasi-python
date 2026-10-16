# Facts the spec-003 review found, verified in the pinned sources

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), box: thirty minutes.
- **Feeds:** `../specifications/003-the-pinned-build-end-to-end.md`
  (Decisions 1, 2, 6, 7, 9).
- **Prompted by:** `../reviews/003-the-pinned-build-end-to-end-spec-2026-10-16.md`
  (findings 2, 3, 4, 5, 8; N1, N3, N8).

## Why

A specification may only rest on research (constitution §5.1). The
review of spec 003 found facts about the pinned sources that change
the build. Each is re-read here in the pinned sources themselves (the
spike's unpacked trees of CPython 3.14.8, numpy 2.5.2 and pandas
3.0.6, unchanged from the tarballs pinned in `downloads/SHA256SUMS`),
so the specification stands on this memo, not on the review's word.

## Findings (READ unless marked)

1. **pandas installs its pure-Python package without an install tag.**
   `pandas/meson.build:43`: `install_subdir(subdir, install_dir:
   py.get_install_dir() / 'pandas')`, with no `install_tag`. So `meson
   install --tags python-runtime` leaves out `pandas/core`,
   `pandas/io` and the rest, which is why the spike's tagged install
   was 536 KB and its zip used the sdist's tree. A full install (no tag
   filter) includes them.
2. **numpy's vendored meson is 1.11.1**
   (`vendored-meson/meson/mesonbuild/coredata.py:47`), older than the
   pinned meson 1.12.1. A build directory belongs to the meson that
   configured it, so numpy's install must run the vendored one.
3. **numpy declares seventeen licence files** in `pyproject.toml`
   `license-files` (lines 53–71): `LICENSE.txt` and the notices of
   libdivide, pythoncapi-compat, highway, dragon4, x86-simd-sort, svml,
   pocketfft, `numpy.ma`, lapack-lite, the random package, its
   distributions, MT19937, PCG64, Philox, SFC64 and SplitMix64. Some
   cover code this build leaves out (highway, x86-simd-sort, svml:
   SIMD is disabled); shipping them all costs a few kilobytes and
   avoids deciding per file what the linker kept.
4. **CPython's WASI driver takes `SOURCE_DATE_EPOCH` from `git log -1`
   of the directory it runs in, and lets the environment override it**
   (`Tools/wasm/wasi/__main__.py:69–79`: `environment = env_defaults |
   os.environ | updates`). Run from this repository, every commit would
   change the build; a constant exported by the build script wins.
5. **`random` seeds itself at import** (`Lib/random.py:941`: `_inst =
   Random()`, which seeds from `os.urandom`). Imported inside Wizer, its
   state would be frozen into the published snapshot and shared by
   every call. numpy's global `RandomState` is created at import the
   same way (READ by the review in `numpy/random/mtrand.pyx`; not
   re-read here).
6. **zipimport caches each archive's directory by path**
   (`Lib/zipimport.py:35,94–95`: `_zip_directory_cache`). In a snapshot
   the cache, with its file offsets, is frozen; the snapshot can only
   import from the very zip it was built against.
7. **wasi-libc's cloudlibc carries its own licence.**
   `libc-bottom-half/cloudlibc/LICENSE` at commit
   `b9ef79d7dbd47c6c5bafdae760823467c2f60b70`: 1,292 bytes, SHA-256
   `c8b789cf5a746611e6300a0cc7750dbf92b61912a709d04e639245f7290656d0`
   (EXECUTED: `curl -sSL <raw URL> | shasum -a 256`, `| wc -c`).
8. **pandas ships thirteen bundled licences** in `LICENSES/` (READ:
   directory listing: BOTTLENECK, DATEUTIL, HAVEN ×2, KLIB, MUSL, NUMPY,
   PACKAGING, PSF, PYPERCLIP, PYUPGRADE, SAS7BDAT, ULTRAJSON), and
   CPython documents its incorporated software in `Doc/license.rst`.

## What it decides

The specification's choices on install tags, the meson used for
numpy's install, the licence sources, the build epoch, the frozen
seeds and the snapshot–zip pair rest on findings 1 to 8.

## One line

Every fact the review raised holds in the pinned sources, and each
now has a decided answer in spec 003.
