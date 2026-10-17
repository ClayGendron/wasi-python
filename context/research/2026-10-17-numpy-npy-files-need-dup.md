# numpy's `.npy` files need `dup`, which WASI preview1 lacks

- **Status:** executed (the failure and its cause), 2026-10-17. The fix is carried by spec 021
  (`recipes/patches/numpy-2.5.2/`) and sent upstream by the owner.
- **Superseded in part (2026-10-17):** the sections "Why it is not fixed here", "What it
  decides" and "One line" describe the state before spec 021; the fix is now carried.
- **Owner:** Clay Gendron
- **Researcher:** the author agent (Claude Opus 5.5), from the data-folders survey's finding.
- **Feeds:** spec 021's carried patch and its guard `test_npy_files_round_trip` (first planned
  as a known gap closed by this memo); `../questions-for-the-owner.md`, question 8 (filing
  the issue upstream is an outward-facing action).
- **Stands on:** `2026-10-16-what-data-folders-the-packages-need.md`, surprise 1.

## The failure (EXECUTED, 3.15 line, snapshot, through `wasi_python.run`)

```
hasattr(os, "dup")               True
os.dup(1)                        OSError: [Errno 58] Not supported
np.save("/a.npy", np.arange(3))  OSError: [Errno 58] Not supported   (a 128-byte header is left)
np.save(io.BytesIO(), ...)       works; np.load of it gives [0 1 2]
np.savez("/a.npz", x=...)        works; np.load("/a.npz")["x"] gives [0 1 2]
```

The 0.1.0a1 set fails the same way (the survey, EXECUTED). `ndarray.tofile` and `np.fromfile`
on a real file fail too; `.npz`, text formats, pickle and in-memory buffers work.

## The cause (READ: numpy 2.5.2)

- `numpy/lib/_format_impl.py`, `write_array`: when `isfileobj(fp)` is true (an `io.FileIO`, or
  a buffered reader or writer whose `fileno()` works), the array is written with
  `array.tofile(fp)`, after the header has already been written through Python.
- `tofile` needs a C `FILE*`. `npy_PyFile_Dup2` (`numpy/_core/include/numpy/npy_3kcompat.h:96`)
  gets one by calling `os.dup(fd)` and `fdopen` on the copy, so it can `fclose` it later
  without closing the caller's file.
- WASI preview1 has no call that duplicates a descriptor (`fd_renumber` moves one). wasi-libc
  answers `dup` with `ENOTSUP`, and CPython's `os.dup` raises it.

## Why it is not fixed here

Every fix inside this project would break a hard rule: patching numpy's source (zero patches),
or a stand-in `os.dup` that pretends to duplicate (it would hand numpy a descriptor that is
the caller's own, and `fclose` would close the caller's file). The fix belongs upstream.

## The upstream fix, as an issue draft

> **`np.save`/`np.load`/`tofile`/`fromfile` fail on WASI: `os.dup` is not supported**
>
> On `wasm32-wasip1` (CPython 3.14 and 3.15, numpy 2.5.2) `os.dup` raises
> `OSError: [Errno 58] Not supported`: WASI preview1 has no descriptor duplication. So
> `np.save` to a path fails after writing the header, and `np.load`, `ndarray.tofile` and
> `np.fromfile` on real files fail the same way. In-memory buffers work.
>
> `write_array` and `read_array` already have a path for file-like objects that are not real
> files (chunked `fp.write(...)` / `fp.read(...)`). A fallback to it when `os.dup` fails (or
> `isfileobj` returning false when `os.dup` is unavailable for the platform) would make `.npy`
> files work on WASI with no change elsewhere. Reproducer: `python -c "import numpy as np;
> np.save('/tmp/a.npy', np.arange(3))"` under wasmtime with a WASI build of numpy.

## What it decides

The judge records the failure as a known gap: a check that round-trips a `.npy` file through
a real path, failing today, with this memo as its closer. The README's platform facts name the
limit and the workaround (save to `io.BytesIO`, or use `np.savez`, which goes through
`zipfile`).

## One line

`.npy` files fail on WASI because numpy duplicates the file descriptor and WASI cannot; the fix
is numpy's to make, and until then the judge names the gap and the README the workaround.
