# The CPython 3.15 + wasi-sdk 33 line

- **Status:** placeholder (research to do), 2026-10-16
- **Owner:** Clay Gendron
- **Blocks:** the toolchain pins of the first release; the matplotlib
  build.

## The question

The spike built CPython 3.14.8 with wasi-sdk 24 and proved the whole
recipe on that line. CPython 3.15.0 (2026-10-09) pins wasi-sdk 33,
whose sysroot ships a libc++ that links C++ exceptions; the spike
executed a throw/catch probe on SDK 33 under wasmtime 49 and it ran.
On the SDK-24 line a C++ `throw` inside numpy's pocketfft aborts the
guest, and matplotlib's Agg and ft2font cannot be built. Does the
whole recipe reproduce on 3.15 + SDK 33, and what changes?

## What answers it

1. Re-run `scripts/00_download.sh` with the 3.15 tarball and the SDK-33
   tarball pinned; re-run the recipe end to end.
2. Build numpy with `-fwasm-exceptions -mllvm -wasm-use-legacy-eh=false`
   and `-lunwind` instead of `recipes/cxa_stubs.c`; confirm a forced
   pocketfft error surfaces as a Python exception, not an abort.
3. Re-run the spike's verification set (study 04's script, `import
   numpy` with zero `.so` opens, the numpy and pandas CSV jobs, the
   `numpy.random` probe, the post-snapshot import) and compare the
   operation counts and sizes with the 3.14 numbers.
4. Record what the 3.15 driver changed (`Tools/wasm/wasi` is now under
   `Platforms/WASI` on main) and whether the `_PYTHON_SYSCONFIGDATA_*`
   trick still introspects.

## What it decides

The first release's pins. Expected: 3.15 + 33 if the re-run costs a
day and the counts match; otherwise 3.14.8 + 24 for the first release and
3.15 + 33 for the next.
