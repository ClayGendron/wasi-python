# What makes the Wizer snapshot differ between builds

- **Status:** executed, 2026-10-16
- **Owner:** Clay Gendron
- **Researcher:** an agent (Claude Opus 5.5), box: two hours (two
  strikes, AGENTS.md rule 7).
- **Feeds:** `../specifications/003-the-pinned-build-end-to-end.md`
  (criterion 2, landing notes); `scripts/compare_snapshots.py`.
- **Machine (benchmark facts only):** Apple arm64, macOS 26.5.

## The question

Spec 003's criterion 2 asks that rebuilding steps 60 to 90 yield
byte-identical `python.wasm`, `python-snapshot.wasm` and
`python-stdlib.zip`. The first rebuild did not: the reactor and the zip
matched, the snapshot did not. What differs, and what can a recipe file
do about it?

## Method (EXECUTED)

Two snapshots built from the same inputs are instantiated with
wasmtime-py (nothing in them runs) and their initial linear memories
compared byte by byte; differing bytes are named through the reactor's
link map (`-Wl,--Map`). Variants of the reactor were linked from a
scratch copy of `recipes/reactor_main.c` with different pre-imports and
fixes, each snapshotted twice. The tool that remains is
`scripts/compare_snapshots.py`.

## Findings

1. **The reactor and the zip are reproducible.** Steps 60–90 run twice,
   and a third time from an empty `build/`, gave the same `python.wasm`
   (`fc69ea30c75139cc…`) and zip every time; CPython's own `python.wasm`
   from step 20 also repeated (`2f3ca731bb2d6a79…`), so clang honours the
   pinned `SOURCE_DATE_EPOCH` (EXECUTED: `shasum -a 256` of each build).
2. **The snapshot first differed in about 20 MB of 57.7 MB** of initial
   memory, almost all heap pointers: allocation diverged early
   (EXECUTED: 1,603,647 differing runs, 19,773,965 bytes).
3. **Even `import encodings` alone differed**, in 2,586 bytes: the
   shadow stack just below 16 MB (dead entropy from seeding `random`), a
   ChaCha state ("expand 32-byte k") and one counter byte (EXECUTED).
4. **The allocator is not the cause of the divergence.** CPython's WASI
   build uses mimalloc (`WITH_MIMALLOC 1`; pymalloc is not compiled in:
   `WITH_PYMALLOC` undefined, READ: `pyconfig.h`). Switching Python to
   `PYMEM_ALLOCATOR_MALLOC` left the 20 MB divergence in place
   (EXECUTED). Hypothesis 1: rejected.
5. **Entropy and clock reads during the imports are the cause.** With
   `os.urandom` and the `time` clocks answering constants while Wizer
   runs the pre-imports, and the real functions restored afterwards
   everywhere a module bound them, the full snapshot differed in 101
   bytes (with `malloc`) instead of 20 MB (EXECUTED). Hypothesis 2:
   confirmed. numpy's `SeedSequence`, for one, sizes a Python int from
   random bits (INFERRED from the divergence starting during numpy's
   import).
6. **With mimalloc kept, what remains is named.** After the pins, a
   cleared stack and mimalloc's main-heap random context fixed before
   Python allocates, two snapshots differ in 392 bytes (EXECUTED:
   `scripts/compare_snapshots.py`):
   - 12 bytes in `_mi_heap_main` (its cookie and keys, set from entropy
     when mimalloc loads), 1 byte in `mi_process_start` (mimalloc's
     start time), 4 bytes in `start` (wasi-libc's emulated process
     clock origin): state the C runtime's constructors capture before
     `wizer.initialize` runs; the last two are file-static.
   - 375 bytes in 153 small runs (1–4 bytes) inside heap blocks: bytes
     past string terminators and in block padding, next to live objects
     (EXECUTED: the words around three of them). None is a pointer and
     nothing reads them. INFERRED: stale bytes left by C-level clock
     reads (a `datetime.now()` inside a C extension, for instance), which
     a Python-level pin cannot reach. **This inference was wrong: see
     finding 8.** Hypothesis 3 (mimalloc's page
     keys) did not remove them: rejected.
7. **Fuel is now exact.** Under the harness's own clock and random
   source, five snapshot runs of `-c pass` spent 117,509,180
   instructions each: a spread of 0 (EXECUTED).

## What it decides

- The reactor keeps the three measures that work: the pins during
  `wizer.initialize` (finding 5), the cleared stack (3), and
  mimalloc's random context fixed before Python allocates (6).
- Criterion 2 holds for `python.wasm` and the zip. For the snapshot it
  holds up to the residue of finding 6: about 0.0007% of its memory,
  never a pointer. That residue is the subject of the placeholder
  memo `2026-10-16-making-the-snapshot-byte-reproducible.md`.

## Addendum after the build review (2026-10-16)

The build review (`../reviews/003-the-pinned-build-end-to-end-2026-10-16.md`,
finding 1) found the source of most of finding 6's heap residue; this
section records it and what followed. The findings above stand as
written, except finding 6's inference.

8. **The heap residue is the Wizer root's file metadata, not clock
   reads.** Several differing words in the reviewer's two snapshots
   equal the `st_mtime` of `build/wizer-root`, which step 80 creates with
   `cp` at build time (EXECUTED by the reviewer: `stat -f %m`). With
   every mtime in two fresh roots set to `SOURCE_DATE_EPOCH`, two
   snapshots differed in 44 bytes: the 17 named C-runtime bytes and 27
   in 9 heap runs (EXECUTED, by the reviewer and again by the author).
   The 9 runs sit in the unused upper bytes of `str` objects' state
   word, and each holds a value below 10^9 that differs per root: a
   stale `st_ctim` nanosecond count, which `touch` cannot set (INFERRED
   from the values). Wizer run twice on **one** root left only the 16
   bytes in the three named regions (EXECUTED): the root's inode and
   change time are the cause.
9. **Pinning the WASI calls themselves removes everything.** The
   reactor's link now wraps `__wasi_clock_time_get`,
   `__wasi_random_get`, `__wasi_path_filestat_get` and
   `__wasi_fd_filestat_get` (`wasm-ld --wrap`, a link flag on our own
   link, no upstream file touched). While a reactor flag is set they
   answer constants (file metadata keeps its size and type but gets
   device 0, inode 0 and fixed times); the flag starts set, so the C
   runtime's constructors are covered too, and is cleared before any
   program runs. Two step-80 runs, each on a fresh root, gave snapshots
   with the same SHA-256 (`5537ea7fd9133d11…`) and 0 differing bytes
   (EXECUTED: `scripts/compare_snapshots.py`). The Python-level clock
   and entropy stand-ins and the mimalloc context fix were removed as
   redundant.
10. **The placeholder memo is answered.**
    `2026-10-16-making-the-snapshot-byte-reproducible.md` records the
    result and the full-build evidence.

## One line

Entropy and clock reads during the snapshot's imports made 20 MB of
difference and file metadata made the rest; pinning the four WASI calls
that report them, at link time, makes the snapshot the same bytes on
every build.
