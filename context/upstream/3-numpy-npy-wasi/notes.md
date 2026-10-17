# Issue 3: numpy `.npy` files on WASI

Status: **code ready; the PR description must be written by the owner**
(NumPy's AI policy, see `pr.md`). Nothing was posted. Base: numpy main at
`ac61120` (2026-10-16).

## The fix

`fix.patch` (2 files, +21):

- `numpy/lib/_format_impl.py`: `import sys`; `isfileobj` returns False when
  `sys.platform == "wasi"`, with a two-line comment.
- `numpy/lib/tests/test_format.py`: `test_save_load_without_dup`,
  parametrized over `basic_arrays + record_arrays` (161 arrays).

`isfileobj` already means "numpy can hand this to `tofile`/`fromfile`": it
returns False for a buffered wrapper whose `fileno()` fails. On WASI the
descriptor exists but cannot be duplicated, so the same answer fits
(INFERRED, from READ code).

## Evidence

All under `evidence/`.

| file | what | label |
|---|---|---|
| `guest-run.txt` | in the real guest: the failure on stock numpy 2.5.2; the patched `isfileobj` applied at run time; the proposed test's body 161/161 (stock 12/161); extra round-trips; byte equality | EXECUTED |
| `guest-memmap-probe.txt` | `open_memmap(file object)` before and after; `mmap` unavailable on WASI | EXECUTED |
| `native-tests-after.txt` | numpy main + patch built natively: new test 161 passed; `test_format` 204 passed, 1 skipped; `test_io` 214 passed, 1 skipped | EXECUTED |
| `native-new-test-without-fix.txt` | the new test with the fix reverted in the installed copy: 149 failed, 12 passed | EXECUTED |
| `ruff.txt` | ruff 0.16.10 (numpy's pinned linter) on both files: clean | EXECUTED |

How the guest run worked (EXECUTED): `scripts/run_in_guest.py` runs on the
host through `wasi_python.run`, from the main repo's venv:

```
WASI_PYTHON_CACHE=/Users/claygendron/Git/Repos/wasi_python/build/cwasm-cache \
  uv run --project /Users/claygendron/Git/Repos/wasi_python \
  python scripts/run_in_guest.py <numpy clone> scripts/guest_check.py
```

It takes `isfileobj`'s source **from the patched clone** (and asserts the
WASI check is in it), the test's arrays and the test function from the
patched `test_format.py`, and sends them with `guest_check.py` as one `-c`
program. In the guest, `_format_impl.sys = sys` stands in for the patch's
`import sys`, and the patched function is `exec`'d into the module's
namespace. The build and the artifacts are not changed. The guest's numpy
is 2.5.2; its `isfileobj` is identical to main's (EXECUTED diff), and the
other differences in `_format_impl.py` do not touch the data path (READ).

Guest facts (EXECUTED): `sys.platform` is `wasi`, `platform.machine()` is
`'wasm32'`, so numpy's `IS_WASM` is already True on WASI. `os.dup(1)` raises
`OSError(58, 'Not supported')`.

The native build (EXECUTED): `uv pip install --no-build-isolation` of the
patched clone with meson-python, Cython 3.3.0 and Apple clang 21; six
submodules fetched shallow (not `scipy-mathjax`). Under a minute.

## Choices, and what I rejected

- **`sys.platform == "wasi"` in `isfileobj`** (chosen). Zero cost elsewhere.
  `sys.platform` is how CPython names WASI (preview 1 and 2 alike).
- **Fallback when `os.dup` raises** (rejected). `write_array` would catch
  `OSError` from `tofile` and retry the chunked path. But `tofile` raises
  `OSError` for real I/O errors too, and the only way to tell "no dup" apart
  is the errno, which is fragile. A retry after a partial write would
  corrupt the file. A probe (`os.close(os.dup(fd))` inside `isfileobj`)
  would work on any platform without dup, but adds two syscalls to every
  save and load everywhere.
- **The check at the three call sites instead of in `isfileobj`**
  (considered). It would leave `open_memmap`'s "cannot use existing file
  handles" `ValueError` unchanged on WASI. Memmap cannot work on WASI
  (EXECUTED: "mmap is unavailable on wasm32-wasi"), so I took the smaller
  diff and named the side effect in `pr.md`. Easy to switch if reviewers
  ask.
- **The emscripten precedent.** NumPy has no Python-level runtime check for
  emscripten in library code (READ, grep). It special-cases wasm in C
  (`__EMSCRIPTEN__`, `__wasm__` in `npy_cpu.h`, `npy_fenv.*`,
  `lowlevel_strided_loops.c.src`) and in tests through `IS_WASM =
  platform.machine() in ["wasm32", "wasm64"]` (`numpy/testing/_private/utils.py:105`).
  Emscripten has `dup`, so it needs no check here. A `sys.platform` check in
  library code is the existing style elsewhere (`numpy/__init__.py`,
  `ctypeslib`).

## `tofile` and `fromfile` called directly

They still fail on WASI with real files (EXECUTED in the guest, stock). They
belong in a separate change (INFERRED, from READ code): both get a `FILE *`
through `npy_PyFile_Dup2` (`npy_3kcompat.h`), which needs `dup` so it can
`fclose` without closing the caller's descriptor. A fix would be C: on
failure to dup, fall back to Python-level `write(arr.tobytes())` /
`readinto`, or on WASI only `fdopen` the descriptor and never `fclose`
it (which leaks the `FILE`). Either needs design discussion, and a WASI
build of numpy to test, which this project's rules keep out of reach here.
Recommend mentioning it in the PR as follow-up, and filing it as an issue.

## How numpy tests platforms (READ)

- Skips use `@pytest.mark.skipif(IS_WASM, reason=…)`; `IS_WASM` is
  `platform.machine()`-based, so it covers WASI too.
- CI: `.github/workflows/emscripten.yml` builds and tests under Pyodide
  (cibuildwheel, `cp314-pyodide_wasm32`). There is no WASI CI job.
- The new test needs no skip. It emulates WASI, so it runs everywhere.
  It uses `monkeypatch`, as `test_fromfile_bad_dup` does; under
  pytest-run-parallel I expect the `monkeypatch` fixture to make it run
  single-threaded (INFERRED, not run in parallel mode).

## Licence and process (READ)

- numpy is BSD-3-Clause. Contributors license their code under it when it
  is merged (`ai_policy.rst`, "Copyright"). No CLA, no DCO sign-off.
- **AI policy** (`doc/source/dev/ai_policy.rst`): disclosure required; PR
  and issue descriptions and comments must not be AI-written; an agent may
  not submit; the submitter must understand and be able to explain the
  code. Non-maintainers may have at most 2 non-draft PRs open.
- PR template: "PR summary", "First time contributor introduction", "AI
  Disclosure". Commit messages start with an acronym (`BUG:` here), lines
  ≤ 72 columns.
- The issue draft in `context/research/2026-10-17-numpy-npy-files-need-dup.md`
  is AI-written; under the same policy it must be rewritten by the owner
  before filing. With a PR this small, the PR alone (referencing gh-25859)
  may be enough.

## Open risks

- Reviewers may prefer the call-site placement (see above), or ask for the
  C-level `tofile`/`fromfile` fallback in the same PR.
- Monkeypatching `sys.platform` in a test is unusual in numpy; a reviewer
  may ask for a private module constant to patch instead.
- Not run under pytest-run-parallel, nor on Linux or Windows (INFERRED fine:
  pure Python).

## One line

`isfileobj` now says no on WASI, so `np.save` and `np.load` of real files
use numpy's existing chunked path instead of `os.dup`; 161 of 161 arrays
round-trip in the real guest and natively, and the owner must write the PR
text himself under numpy's AI policy.
