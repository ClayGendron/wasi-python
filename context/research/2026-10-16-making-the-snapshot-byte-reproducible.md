# Making the snapshot byte-reproducible

- **Status:** executed, 2026-10-16 (written as a placeholder the same
  day, completed in place after spec 003's build review)
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), after the build
  review's finding 1
  (`../reviews/003-the-pinned-build-end-to-end-2026-10-16.md`).
- **Blocks:** the claim that a published `python-snapshot.wasm` can be
  rebuilt to the same SHA-256; the reproducible-builds memo's snapshot
  comparison.
- **Stands on:** `2026-10-16-what-makes-the-snapshot-differ.md`
  (findings 6, 8 and 9).
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5.

## The question

After spec 003's first build, two builds of the snapshot differed in
about 400 bytes: 17 in three C-runtime regions set by load-time
constructors (`_mi_heap_main`, `mi_process_start`, wasi-libc's `start`),
and the rest in small runs of stale bytes inside heap blocks. Can the
snapshot be made byte-identical without patching an upstream tree?

## What was planned

1. Find the C-level clock and entropy reads during `wizer.initialize`.
2. Decide a recipe-level answer for each.
3. Try CPython's `--without-mimalloc`.
4. Ask whether Wizer can answer WASI calls deterministically.

## Findings

1. **The heap runs came from file metadata, not clock reads.** The
   build review traced most of them to the mtimes of the Wizer root;
   with those fixed, the rest followed the root's inode and change time
   (`2026-10-16-what-makes-the-snapshot-differ.md`, finding 8;
   EXECUTED). So step 1's premise was wrong, and steps 3 and 4 were not
   needed.
2. **One recipe-level answer covers every source: wrap the four WASI
   calls that report them.** `wasm-ld --wrap=<symbol>` on the reactor's
   own link (a flag in `scripts/steps/60_link.sh`, no upstream file
   touched) sends every call of `__wasi_clock_time_get`,
   `__wasi_random_get`, `__wasi_path_filestat_get` and
   `__wasi_fd_filestat_get` to `recipes/reactor_main.c`. While a flag
   there is set, the clocks answer `SOURCE_DATE_EPOCH` or 0, entropy
   answers zeros, and file metadata keeps its size and type but has
   device 0, inode 0 and fixed times; otherwise the calls pass through.
   (READ: wasi-sdk 24's `libc.a` defines the four functions in its own
   objects and calls them from others, so `--wrap` reaches every
   caller: `llvm-nm` shows them as `T` once and `U` elsewhere.)
3. **The flag starts set, so the constructors are covered.** mimalloc's
   heap keys and start time and wasi-libc's process-clock origin are
   captured before any entry point runs; with the flag set from the
   start they capture constants. `run` clears the flag before Python
   starts, and `wizer.initialize` clears it once the imports are done,
   so no program sees a pinned value (checked by
   `test_a_program_sees_real_entropy_and_file_metadata` on both
   binaries).
4. **Two step-80 runs now give the same snapshot.** Each run creates a
   fresh Wizer root, with a new inode and new times. Two consecutive
   runs gave `5537ea7fd9133d11…` both times, and
   `scripts/compare_snapshots.py` found 0 differing bytes (EXECUTED).
   The full-build evidence is in spec 003's landing notes.
5. **What the wrap replaced.** The first build's Python-level stand-ins
   for `os.urandom` and the `time` clocks, their restore pass, and the
   direct reset of mimalloc's random context are gone. The restore was
   inexact (the build review's finding 5), and the wrap needs none of
   them.

## What it decides

`SHA256SUMS` can promise a rebuildable snapshot, as it does the reactor
and the zip. `scripts/compare_snapshots.py` keeps an empty allowance
list and serves to say where two snapshots differ if they ever do.

## One line

Wrapping the four WASI calls that report time, entropy and file
metadata, at link time, makes the snapshot the same bytes on every
build, and no program ever sees the pinned values.
