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

## The amendment (2026-10-18, spec 051, Decision 10)

Not yet sent, so the carried patch
(`recipes/patches/numpy-2.5.2/0001-npy-files-without-dup.patch`) was amended in place after
numpy's own tests, run in the guest, found two behaviour changes. `fix.patch` above predates it;
it is remade from the carried patch when the change is rebased onto `main`. Three facts to add:

- **One predicate, and the subclass rule.** Native `isfileobj` tests two things: the object is a
  `FileIO`, `BufferedReader` or `BufferedWriter`, and its `fileno()` succeeds. Both become one
  private predicate, `_is_real_file(f)`; `isfileobj(f)` is `_is_real_file(f) and sys.platform !=
  "wasi"`. Before the amendment, real files on WASI went down the chunked path whatever the
  array's type, so `np.save(path, masked_array)` wrote the data and dropped the mask: data loss
  where native numpy raises, because `MaskedArray.tofile` raises `NotImplementedError` (EXECUTED
  in the guest, spec 051: `saved [1 2 3] ndarray`). Now, in `write_array` on WASI, when
  `_is_real_file(fp)` and `type(array).tofile is not ndarray.tofile`, the subclass's own `tofile`
  decides (`array.T.tofile(fp)` for a Fortran-ordered array, as native's branch does). A
  `BufferedWriter` over a `BytesIO` is not a real file there either, as natively. Only numpy's
  `MaskedArray` overrides `tofile` in numpy and pandas (READ). New test:
  `test_save_masked_without_dup` (a masked array to a path raises; to
  `BufferedWriter(BytesIO())` it is written).
- **A truncated real file's message on WASI.** A real file is now read the way numpy reads every
  in-memory stream, so a truncated one raises `ValueError: EOF: reading array data, expected 48
  bytes got 47`, where natively a real file raises `ValueError: Failed to read all data for
  array. …`. The type is the same; changing the message would add WASI-only code to the reader.
  This project documents it as a platform fact.
- **`test_file_truncated`.** It expects the native message, so it would fail on WASI once numpy
  takes the change. On WASI its pattern also accepts the in-memory message, behind `if
  sys.platform == "wasi"`; elsewhere it is unchanged.

Evidence (EXECUTED, spec 051's revision runs, under the pinned oracle: Python 3.15.0, numpy
2.5.2, with `sys.platform` set to `"wasi"` and `os.dup` raising): `test_file_truncated`,
`test_save_masked_without_dup` and `test_save_load_without_dup` (161 arrays) pass with the amended
module. In the guest, spec 051's build: a masked array saved to a path raises native's
`NotImplementedError: MaskedArray.tofile() not implemented yet.`, and every round trip of
`tests/checks/test_v1_3_data_stack.py::test_npy_files_round_trip` still passes.

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
