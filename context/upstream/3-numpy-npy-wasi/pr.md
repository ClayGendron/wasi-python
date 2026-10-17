# numpy PR: material for the owner to write from

> **Read first.** NumPy's AI policy (`doc/source/dev/ai_policy.rst`) says:
> "do not use AI to automatically generate comments, pull request
> descriptions, or issue descriptions", "The use of an AI agent that writes
> code and then submits a pull request autonomously is not permitted", and
> every PR must carry an AI disclosure. So this file is **not** a PR
> description to paste. It is the facts, laid out under NumPy's template
> headings, for you to write the description in your own words. The code
> itself may be AI-assisted if you understand it and disclose it.

## Title

`BUG: use the file-like path for .npy files on WASI`

## Commit message (convention: acronym prefix, 72-column lines)

Policy covers PR and issue descriptions, not commit messages, but rewrite
this too if you prefer.

```
BUG: use the file-like path for .npy files on WASI

WASI has no way to duplicate a file descriptor, so os.dup raises
OSError (ENOTSUP) there. write_array and read_array send real files
to tofile and fromfile, which need os.dup, so np.save to a path
failed after writing the header, and np.load of a path failed.

isfileobj now returns False on WASI, so real files are read and
written in chunks, as other file-like objects already are.
```

## PR summary: the facts to cover

- **Problem.** On `wasm32-wasip1`, `os.dup` exists but raises
  `OSError: [Errno 58] Not supported`. WASI preview 1 has no call that
  duplicates a descriptor. `np.save(path, a)` writes the 128-byte header,
  then fails in `a.tofile(fp)`; `np.load(path)` fails in `np.fromfile`.
  Both go through `npy_PyFile_Dup2`, which calls `os.dup`.
- **Fix.** `isfileobj` returns False when `sys.platform == "wasi"`.
  `write_array` and `read_array` already have a chunked path for
  file-likes that are not real files (BytesIO, gzip). Real files on WASI
  now take it. Five lines; no change on any other platform.
- **Test.** `test_save_load_without_dup` in `numpy/lib/tests/test_format.py`
  sets `sys.platform` to `"wasi"` and makes `os.dup` raise `ENOTSUP`, then
  round-trips every array in `basic_arrays + record_arrays` through a
  real path. It runs on every CI platform, Pyodide included. It follows
  `test_fromfile_bad_dup` in `test_multiarray.py`, which also monkeypatches
  `os.dup`.
- **Evidence.**
  - Native (macOS arm64, Python 3.14.2, numpy main `ac61120` built from
    source): the new test passes 161 of 161 with the fix, and fails 149 of
    161 without it (the 12 that pass are object arrays, which are
    pickled). `test_format.py`: 204 passed, 1 skipped; `test_io.py`: 214 passed, 1 skipped.
    ruff 0.16.10: clean.
  - In a real WASI guest (CPython 3.15.0 for `wasm32-wasip1`, numpy 2.5.2
    built in, under Wasmtime 49), with the patched `isfileobj` applied at
    run time: the test's body passes 161 of 161 with no monkeypatching,
    against 12 of 161 with stock numpy. Also round-tripped: Fortran order,
    0-d, zero-size, big-endian, unicode, structured, a 3 MiB array (more
    than `BUFFER_SIZE`), and two arrays through one open file. The file's
    bytes equal an in-memory save's.
- **Side effect to mention.** `open_memmap(file_object)` on WASI now fails
  with `TypeError` instead of the `ValueError` "Memmap cannot use existing
  file handles". Memmap cannot work on WASI anyway: CPython's `mmap` raises
  "mmap is unavailable on wasm32-wasi". If reviewers prefer, the check can
  move from `isfileobj` to the three data call sites instead.
- **Not in this PR.** `ndarray.tofile` and `np.fromfile` called directly
  on real files still fail on WASI. They need a `FILE *`, which needs `dup`
  so it can be closed without closing the caller's file. Fixing them means
  a fallback in C (`npy_PyFile_Dup2` and its callers). That is a separate,
  larger change, best discussed in an issue first.
- **Context.** gh-25859 ("ENH: WASI Build"): a maintainer wrote "If
  there's anything concrete in NumPy to do, I think we'd be happy to
  consider it." No existing issue covers `os.dup` on WASI (searched
  "wasi", "os.dup").
- **Release note.** Probably none needed for a bug fix. If asked:
  `doc/release/upcoming_changes/<PR>.improvement.rst`, a heading such as
  "``np.save`` and ``np.load`` work with files on WASI" and one sentence.

## First time contributor introduction

Yours to write: who you are, the wasi_python project (CPython with numpy
and pandas built in, for `wasm32-wasip1`), and how you use numpy there.

## AI Disclosure: the facts

- Tool: Claude (Anthropic), Claude Opus 5.5, run as a coding agent.
- What it did: traced the failure to `npy_PyFile_Dup2`, wrote the
  five-line change and the test, built numpy and ran the tests natively,
  and ran the change inside a WASI guest.
- What is AI-generated: the code change and the test (all of
  `fix.patch`). The description must be yours.
- What you checked: say what you reviewed and re-ran yourself.
